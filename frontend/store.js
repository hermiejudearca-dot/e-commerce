
'use strict';


const IS_VS_CODE_LIVE_SERVER =
  window.location.port === "5500" ||
  window.location.port === "5501";

const ROOT = IS_VS_CODE_LIVE_SERVER
  ? `${window.location.protocol}//${window.location.hostname}:8000`
  : "https://e-commerce-w987.onrender.com";

const API = `${ROOT}/api/store/`;

const CHECKOUT_BACKEND_READY = true;


// ==========================================================
// 2. SHIPPING CONFIGURATION
// ==========================================================

// These values match storefront/views.py.
//
// First item: ₱50
// Each additional item: ₱20

const FIRST_ITEM_DELIVERY_FEE = 50;
const ADDITIONAL_ITEM_DELIVERY_FEE = 20;

// Compatibility with existing code.
const DELIVERY_FEE = FIRST_ITEM_DELIVERY_FEE;

function calculateDeliveryFee(totalQuantity) {
  const quantity = Number(totalQuantity);

  if (!Number.isInteger(quantity) || quantity <= 0) {
    return 0;
  }

  return (
    FIRST_ITEM_DELIVERY_FEE +
    (quantity - 1) * ADDITIONAL_ITEM_DELIVERY_FEE
  );
}


// ==========================================================
// 3. GENERAL HELPERS
// ==========================================================

const $ = id => document.getElementById(id);

const html = value =>
  String(value ?? '').replace(
    /[&<>"']/g,
    char => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;'
    })[char]
  );

const peso = value =>
  '₱' + Number(value || 0).toLocaleString(
    'en-PH',
    {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }
  );

function positiveInteger(value) {
  const number = Number(value);

  return Number.isInteger(number) && number >= 1
    ? number
    : null;
}


// ==========================================================
// 4. APPLICATION STATE
// ==========================================================

// Currently logged-in customer.
let user = null;

// Data loaded from Django.
let products = [];
let cart = [];
let favorites = [];
let addresses = [];

// Current product selected for review.
let reviewProduct = null;

// Checkout mode:
// 'cart' = selected shopping cart items
// 'buy'  = Buy Now product
let checkoutMode = 'cart';
let buyNowItem = null;

// Delivery address state.
let selectedAddressId = null;
let addressReturnPage = 'account';
let addressFeatureAvailable = true;

// Prevent duplicate order submissions.
let submittingOrder = false;


// ==========================================================
// 5. CART SELECTION STATE
// ==========================================================

// Store cart-item IDs, not product IDs.
let selectedCartItemIds = new Set();

// Automatically select available products on the
// first cart load. Preserve selection afterward.
let cartSelectionInitialized = false;


// ==========================================================
// 6. AUTOMATIC QUANTITY SAVING STATE
// ==========================================================

// Prevent overlapping saves for the same cart item.
const savingCartItemIds = new Set();


// ==========================================================
// 7. CART SELECTION HELPERS
// ==========================================================

function selectedCartItems() {
  return cart.filter(item =>
    selectedCartItemIds.has(Number(item.id)) &&
    !itemHasStockProblem(item)
  );
}

function selectedCartQuantity() {
  return selectedCartItems().reduce(
    (sum, item) => sum + Number(item.quantity),
    0
  );
}

function selectedCartSubtotal() {
  return selectedCartItems().reduce(
    (sum, item) =>
      sum +
      Number(item.product.price) *
      Number(item.quantity),
    0
  );
}

function selectedCartDeliveryFee() {
  return calculateDeliveryFee(
    selectedCartQuantity()
  );
}

function selectedCartTotal() {
  return (
    selectedCartSubtotal() +
    selectedCartDeliveryFee()
  );
}

function availableCartItems() {
  return cart.filter(
    item => !itemHasStockProblem(item)
  );
}


// ==========================================================
// 8. PAGE CONFIGURATION
// ==========================================================

// Each page name maps to an HTML section ID.
//
// Example:
// 'favorites' -> id="favoritesPage"

const pages = [
  'shop',
  'login',
  'register',
  'cart',
  'favorites',
  'orders',
  'checkout',
  'review',
  'writeReview',
  'account',
  'address'
];

const protectedPages = [
  'cart',
  'favorites',
  'orders',
  'checkout',
  'writeReview',
  'account',
  'address'
];


// ==========================================================
// 9. NOTIFICATIONS
// ==========================================================

function notify(message) {
  const notice = $('notice');

  if (notice) {
    notice.textContent = message;
  }

  window.scrollTo({
    top: 0,
    behavior: 'smooth'
  });
}

function clearNotice() {
  const notice = $('notice');

  if (notice) {
    notice.textContent = '';
  }
}


// ==========================================================
// 10. COOKIE / SECURITY HELPERS
// ==========================================================

function cookie(name) {
  return document.cookie
    .split('; ')
    .find(item => item.startsWith(name + '='))
    ?.slice(name.length + 1) || '';
}


// ==========================================================
// 11. IMAGE HELPERS
// ==========================================================

function imageURL(value) {
  if (!value) {
    return '';
  }

  try {
    const url = new URL(value, ROOT);

    if (!['http:', 'https:'].includes(url.protocol)) {
      return '';
    }

    return url.href;
  } catch {
    return '';
  }
}

function productImage(product, className = '') {
  const src = imageURL(product?.image);

  if (!src) {
    return `
      <div class="product-placeholder ${html(className)}">
        🍩
      </div>
    `;
  }

  return `
    <img
      class="${html(className)}"
      src="${html(src)}"
      alt="${html(
        product?.name || 'Honeybail product'
      )}"
      loading="lazy"
      onerror="
        this.onerror=null;
        this.hidden=true;
        this.insertAdjacentHTML(
          'afterend',
          '<span aria-hidden=&quot;true&quot;>🍩</span>'
        );
      "
    >
  `;
}


// ==========================================================
// 12. PRODUCT HELPERS
// ==========================================================

function findProduct(id) {
  return products.find(
    product => Number(product.id) === Number(id)
  );
}

function productStock(product) {
  return Math.max(
    0,
    Number(product?.stock || 0)
  );
}

function validQuantity(value, max) {
  const quantity = Number(value);

  if (!Number.isInteger(quantity) || quantity < 1) {
    throw Error(
      'Please enter a valid quantity of at least 1.'
    );
  }

  if (quantity > max) {
    throw Error(
      `Only ${max} item(s) are available.`
    );
  }

  return quantity;
}

function itemHasStockProblem(item) {
  const quantity = Number(item.quantity);
  const stock = productStock(item.product);

  return (
    item.product?.is_active === false ||
    stock < 1 ||
    !Number.isInteger(quantity) ||
    quantity < 1 ||
    quantity > stock
  );
}


// ==========================================================
// 13. DJANGO API REQUESTS
// ==========================================================

// All requests include session cookies.
//
// POST, PATCH, and DELETE initialize CSRF protection
// and send Django's CSRF token.

async function req(path, method = 'GET', data) {
  const headers = {};

  if (method !== 'GET') {
    let csrfResponse;

    try {
      csrfResponse = await fetch(
        API + 'csrf/',
        {
          credentials: 'include'
        }
      );
    } catch {
      throw Error(
        'Cannot connect to Django CSRF endpoint.'
      );
    }

    if (!csrfResponse.ok) {
      throw Error(
        'Could not initialize request security.'
      );
    }

    const csrfToken = cookie('csrftoken');

    if (!csrfToken) {
      throw Error(
        'CSRF token unavailable. Check Django cookie settings.'
      );
    }

    headers['X-CSRFToken'] = csrfToken;
    headers['Content-Type'] = 'application/json';
  }

  let response;

  try {
    response = await fetch(
      API + path,
      {
        method,
        credentials: 'include',
        headers,
        ...(data === undefined
          ? {}
          : {
              body: JSON.stringify(data)
            })
      }
    );
  } catch {
    throw Error(
      'Cannot connect to Django. Check that runserver is running.'
    );
  }

  const result = await response.json()
    .catch(() => ({}));

  if (!response.ok) {
    throw Error(
      result.error ||
      result.detail ||
      `Request failed: HTTP ${response.status}`
    );
  }

  return result;
}


// ==========================================================
// 14. ASYNC ACTION WRAPPER
// ==========================================================

async function act(callback) {
  try {
    await callback();
  } catch (error) {
    console.error(error);

    notify(
      error.message ||
      'Something went wrong.'
    );
  }
}


// ==========================================================
// END OF PART 1 OF 8
//
// NEXT: PART 2 — NAVIGATION, SESSION,
// PRODUCT DISPLAY AND SHOPPING CART
// ==========================================================

/*
============================================================
 HONEYBAIL CUSTOMER STOREFRONT
 ICE BLUE EDITION

 PART 2 OF 8

 NAVIGATION
 CUSTOMER SESSION
 PRODUCT DISPLAY
 FAVORITES HEART STATE
 SHOPPING CART
 AUTOMATIC QUANTITY SAVING
============================================================
*/


// ==========================================================
// 15. PAGE NAVIGATION
// ==========================================================

function page(name) {
  if (!pages.includes(name)) {
    name = 'shop';
  }

  // Keep private customer pages protected.
  if (protectedPages.includes(name) && !user) {
    name = 'login';
    notify('Please log in to continue.');
  }

  // Display the selected page.
  for (const item of pages) {
    const section = $(item + 'Page');

    if (section) {
      section.hidden = item !== name;
    }
  }

  // Only show the shop hero on the Shop page.
  const hero = $('hero');

  if (hero) {
    hero.hidden = name !== 'shop';
  }

  // Load data when opening a page.
  if (name === 'cart' && user) {
    act(loadCart);
  }

  if (name === 'favorites' && user) {
    act(loadFavorites);
  }

  if (name === 'orders' && user) {
    act(loadOrders);
  }

  if (name === 'account' && user) {
    act(loadAccount);
  }

  if (name === 'checkout' && user) {
    act(loadCheckout);
  }

  if (name === 'review') {
    // Review loading is handled by the Reviews button.
  }

  window.scrollTo({
    top: 0,
    behavior: 'smooth'
  });
}


// ==========================================================
// 16. CUSTOMER IDENTITY
// ==========================================================

function identity() {
  const accountButton = $('account');
  const logoutButton = $('logout');

  if (accountButton) {
    accountButton.textContent = user
      ? '👤 My Account'
      : 'Login';

    accountButton.dataset.page = user
      ? 'account'
      : 'login';
  }

  if (logoutButton) {
    logoutButton.hidden = !user;
  }

  // Update any optional account-name display.
  const accountName = $('accountName');

  if (accountName) {
    accountName.textContent = user
      ? user.name || 'Customer'
      : 'Guest';
  }

  const accountEmail = $('accountEmail');

  if (accountEmail) {
    accountEmail.textContent = user
      ? user.email || ''
      : '';
  }
}


// ==========================================================
// 17. CUSTOMER SESSION
// ==========================================================

async function session() {
  try {
    const data = await req('me/');

    user = data.customer || null;
  } catch (error) {
    user = null;

    console.warn(
      'Unable to restore customer session:',
      error.message
    );
  }

  identity();
}


// ==========================================================
// 18. LOAD PRODUCTS
// ==========================================================

async function loadProducts() {
  try {
    const data = await req('products/');

    products = Array.isArray(data.products)
      ? data.products
      : [];

    // Render the product cards using the current
    // saved Favorites state.
    renderProducts();

    // Refresh any product-related panels that exist.
    if (typeof renderFavorites === 'function') {
      renderFavorites();
    }
  } catch (error) {
    const container = $('products');

    if (container) {
      container.textContent =
        'Unable to load products: ' + error.message;
    }

    throw error;
  }
}


// ==========================================================
// 19. CHECK WHETHER A PRODUCT IS FAVORITED
// ==========================================================

// Django returns Favorites in this format:
//
// {
//   "favorites": [
//     {
//       "product": {
//         "id": 1,
//         "name": "Product name"
//       }
//     }
//   ]
// }

function isProductFavorited(productId) {
  const id = Number(productId);

  return favorites.some(item => {
    const savedProduct =
      item.product || item;

    return Number(savedProduct.id) === id;
  });
}


// ==========================================================
// 20. PRODUCT CARD
// ==========================================================

function productCard(product) {
  const available = productStock(product);

  const soldOut =
    available < 1 ||
    product.is_active === false;

  const favorited = isProductFavorited(product.id);

  const rating = Number(product.average_rating || 0);

  const ratingLabel = rating > 0
    ? rating.toFixed(1)
    : 'New';

  return `
    <article class="product">

      <div class="productimage">
        ${productImage(product)}
      </div>

      <div class="productbody">

        <span class="category">
          ${html(product.category || 'Sweet Treats')}
        </span>

        <h3>
          ${html(product.name)}
        </h3>

        <div class="muted product-description">
          ${html(product.description || '')}
        </div>

        <p class="price">
          ${peso(product.price)}
        </p>

        <p class="muted product-meta">
          ${
            soldOut
              ? 'Out of stock'
              : `${available} available`
          }

          · ⭐ ${ratingLabel}
          (${Number(product.review_count || 0)})
        </p>

        <div class="actions product-actions">

          <button
            type="button"
            class="outline"
            data-action="add"
            data-id="${Number(product.id)}"
            ${soldOut ? 'disabled' : ''}
          >
            Add to Cart
          </button>

          <button
            type="button"
            class="primary"
            data-action="buy"
            data-id="${Number(product.id)}"
            ${soldOut ? 'disabled' : ''}
          >
            Buy Now
          </button>

          <button
            type="button"
            class="favorite-button ${
              favorited ? 'is-favorite' : ''
            }"
            data-action="fav"
            data-id="${Number(product.id)}"
            aria-label="${
              favorited
                ? 'Remove from favorites'
                : 'Add to favorites'
            }"
            aria-pressed="${favorited}"
            title="${
              favorited
                ? 'Saved to Favorites'
                : 'Add to Favorites'
            }"
          >
            <span aria-hidden="true">
              ${favorited ? '♥' : '♡'}
            </span>
          </button>

          <button
            type="button"
            class="outline"
            data-action="reviews"
            data-id="${Number(product.id)}"
          >
            Reviews
          </button>

        </div>

      </div>

    </article>
  `;
}


// ==========================================================
// 21. RENDER PRODUCTS
// ==========================================================

function renderProducts() {
  const container = $('products');

  if (!container) {
    return;
  }

  container.innerHTML = products.length
    ? products.map(productCard).join('')
    : '<p>No active products yet.</p>';
}


// ==========================================================
// 22. LOAD SHOPPING CART
// ==========================================================

async function loadCart() {
  if (!user) {
    cart = [];

    selectedCartItemIds.clear();
    cartSelectionInitialized = false;

    updateCartCount();
    renderCart();

    return;
  }

  const data = await req('cart/');

  cart = Array.isArray(data.items)
    ? data.items
    : [];

  const availableIds = new Set(
    availableCartItems().map(
      item => Number(item.id)
    )
  );

  // Remove selections for items that no longer
  // exist or are no longer available.
  for (const id of selectedCartItemIds) {
    if (!availableIds.has(id)) {
      selectedCartItemIds.delete(id);
    }
  }

  // Select available items on the first load.
  // Preserve the customer's selection afterward.
  if (!cartSelectionInitialized) {
    selectedCartItemIds = new Set(availableIds);

    cartSelectionInitialized = true;
  }

  updateCartCount();
  renderCart();
}


// ==========================================================
// 23. UPDATE CART COUNT
// ==========================================================

function updateCartCount() {
  const badge = $('cartCount');

  if (!badge) {
    return;
  }

  const quantity = cart.reduce(
    (sum, item) =>
      sum + Number(item.quantity || 0),
    0
  );

  badge.textContent = String(quantity);
}


// ==========================================================
// 24. SELECT CART ITEMS
// ==========================================================

function toggleCartItemSelection(itemId, checked) {
  const id = Number(itemId);

  const item = cart.find(
    entry => Number(entry.id) === id
  );

  if (!item || itemHasStockProblem(item)) {
    return;
  }

  if (checked) {
    selectedCartItemIds.add(id);
  } else {
    selectedCartItemIds.delete(id);
  }

  renderCart();
}


function toggleSelectAllCart(checked) {
  if (checked) {
    for (const item of availableCartItems()) {
      selectedCartItemIds.add(Number(item.id));
    }
  } else {
    selectedCartItemIds.clear();
  }

  renderCart();
}


// ==========================================================
// 25. AUTOMATIC CART QUANTITY UPDATE
// ==========================================================

async function changeCartQuantity(itemId, change) {
  const id = Number(itemId);

  if (savingCartItemIds.has(id)) {
    return;
  }

  const item = cart.find(
    entry => Number(entry.id) === id
  );

  if (!item) {
    throw Error('Cart item not found.');
  }

  const oldQuantity = Number(item.quantity);
  const stock = productStock(item.product);

  const newQuantity =
    oldQuantity + Number(change);

  if (!Number.isInteger(newQuantity)) {
    throw Error('Invalid quantity.');
  }

  if (newQuantity < 1) {
    return;
  }

  if (
    item.product?.is_active === false ||
    stock < 1
  ) {
    throw Error(
      'This product is currently unavailable.'
    );
  }

  if (newQuantity > stock) {
    notify(`Only ${stock} item(s) are available.`);
    return;
  }

  savingCartItemIds.add(id);

  // Show the new quantity immediately.
  item.quantity = newQuantity;

  updateCartCount();
  renderCart();

  try {
    await req(
      'cart/',
      'PATCH',
      {
        item_id: id,
        quantity: newQuantity
      }
    );

    await loadCart();
  } catch (error) {
    // Restore the previous display if saving fails.
    item.quantity = oldQuantity;

    updateCartCount();
    renderCart();

    throw error;
  } finally {
    savingCartItemIds.delete(id);

    renderCart();
  }
}


// ==========================================================
// 26. ADD PRODUCT TO CART
// ==========================================================

async function addToCart(productId) {
  if (!user) {
    page('login');

    notify(
      'Please log in to add products to your cart.'
    );

    return;
  }

  await req(
    'cart/',
    'POST',
    {
      product_id: Number(productId),
      quantity: 1
    }
  );

  await loadCart();

  notify('Added to your cart! ♡');
}


// ==========================================================
// 27. REMOVE CART ITEM
// ==========================================================

async function removeCartItem(itemId) {
  const id = Number(itemId);

  if (savingCartItemIds.has(id)) {
    return;
  }

  await req(
    'cart/',
    'DELETE',
    {
      item_id: id
    }
  );

  selectedCartItemIds.delete(id);

  await loadCart();

  notify('Item removed from your cart.');
}


// ==========================================================
// END OF PART 2 OF 8
//
// NEXT: PART 3 — CART DESIGN,
// SELECTED ITEMS AND ORDER SUMMARY
// ==========================================================

/*
============================================================
 HONEYBAIL CUSTOMER STOREFRONT
 ICE BLUE EDITION

 PART 3 OF 8

 CART LAYOUT
 ITEM SELECTION
 QUANTITY CONTROLS
 LIVE ORDER SUMMARY
============================================================
*/


// ==========================================================
// 28. RENDER CART PRODUCT ROW
// ==========================================================

function cartItemHTML(item) {
  const product = item.product || {};

  const id = Number(item.id);
  const quantity = Number(item.quantity);
  const stock = productStock(product);

  const unavailable = itemHasStockProblem(item);

  const selected =
    selectedCartItemIds.has(id) &&
    !unavailable;

  const saving = savingCartItemIds.has(id);

  const subtotal =
    Number(product.price || 0) * quantity;

  return `
    <article class="cartrow cart-item
      ${selected ? 'is-selected' : ''}
      ${unavailable ? 'is-unavailable' : ''}">

      <div class="cart-selection">

        <input
          type="checkbox"
          class="cart-item-checkbox"
          data-id="${id}"
          aria-label="Select ${html(product.name || 'product')}"
          ${selected ? 'checked' : ''}
          ${unavailable || saving ? 'disabled' : ''}
        >

      </div>

      <div class="cart-product">

        <div class="cart-thumbnail">
          ${productImage(product)}
        </div>

        <div class="cart-details">

          <strong>
            ${html(product.name || 'Product')}
          </strong>

          <p class="muted">
            ${peso(product.price)} each
          </p>

          ${unavailable ? `
            <p class="cart-stock-warning">
              ${
                stock < 1
                  ? 'Out of stock'
                  : `Only ${stock} available`
              }
            </p>
          ` : ''}

          <p class="cart-item-subtotal">
            ${peso(subtotal)}
          </p>

        </div>

      </div>

      <div class="cart-controls">

        <div class="cart-quantity-editor">

          <button
            type="button"
            class="cart-quantity-button"
            data-action="qty-minus"
            data-id="${id}"
            aria-label="Decrease quantity"
            ${quantity <= 1 || saving ? 'disabled' : ''}
          >
            −
          </button>

          <span
            class="cart-quantity-value"
            aria-live="polite"
          >
            ${quantity}
          </span>

          <button
            type="button"
            class="cart-quantity-button"
            data-action="qty-plus"
            data-id="${id}"
            aria-label="Increase quantity"
            ${
              unavailable ||
              quantity >= stock ||
              saving
                ? 'disabled'
                : ''
            }
          >
            +
          </button>

        </div>

        ${saving ? `
          <span class="muted cart-saving">
            Saving...
          </span>
        ` : ''}

        <button
          type="button"
          class="cart-remove-button"
          data-action="remove"
          data-id="${id}"
          ${saving ? 'disabled' : ''}
        >
          Remove
        </button>

      </div>

    </article>
  `;
}


// ==========================================================
// 29. RENDER CART ORDER SUMMARY
// ==========================================================

function renderCartTotals() {
  const container = $('cartTotal');
  const checkoutButton = $('checkoutStart');

  if (!container) {
    return;
  }

  const items = selectedCartItems();
  const quantity = selectedCartQuantity();
  const subtotal = selectedCartSubtotal();
  const shipping = selectedCartDeliveryFee();
  const total = selectedCartTotal();

  const saving = savingCartItemIds.size > 0;

  container.innerHTML = `
    <div class="cart-summary-content">

      <div class="cart-total-line">
        <span>Selected Items (${quantity})</span>
        <strong>${peso(subtotal)}</strong>
      </div>

      <div class="cart-total-line">
        <span>Shipping</span>
        <strong>${peso(shipping)}</strong>
      </div>

      <div class="cart-total-line cart-grand-total">
        <span>Grand Total</span>
        <strong>${peso(total)}</strong>
      </div>

      <p class="muted cart-shipping-note">
        ₱50 for the first unit and ₱20
        for every additional unit.
      </p>

      ${saving ? `
        <p class="muted">
          Saving your cart changes...
        </p>
      ` : ''}

    </div>
  `;

  if (checkoutButton) {
    checkoutButton.disabled =
      !CHECKOUT_BACKEND_READY ||
      items.length === 0 ||
      saving ||
      submittingOrder;

    checkoutButton.textContent = saving
      ? 'Updating Cart...'
      : items.length > 0
        ? `Checkout Selected (${quantity} items) →`
        : 'Select Available Items to Checkout';
  }
}


// ==========================================================
// 30. RENDER COMPLETE CART
// ==========================================================

function renderCart() {
  const container = $('cartItems');

  if (!container) {
    return;
  }

  const available = availableCartItems();
  const selected = selectedCartItems();

  const allSelected =
    available.length > 0 &&
    available.every(item =>
      selectedCartItemIds.has(Number(item.id))
    );

  const selectAllHTML = cart.length
    ? `
      <div class="cart-select-all">

        <label class="cart-select-label">

          <input
            id="selectAllCart"
            type="checkbox"
            ${allSelected ? 'checked' : ''}
            ${available.length === 0 ? 'disabled' : ''}
          >

          <strong>Select All Available</strong>

        </label>

        <span class="cart-selection-count">
          ${selected.length} of ${available.length}
          available product(s) selected
        </span>

      </div>
    `
    : '';

  const itemsHTML = cart.length
    ? cart.map(cartItemHTML).join('')
    : `
      <div class="cart-empty">

        <h3>Your shopping cart is empty.</h3>

        <p>
          Discover something sweet in our shop!
        </p>

        <button
          type="button"
          class="primary"
          data-page="shop"
        >
          Continue Shopping
        </button>

      </div>
    `;

  container.innerHTML =
    selectAllHTML + itemsHTML;

  renderCartTotals();
}


// ==========================================================
// END OF PART 3 OF 8
//
// NEXT: PART 4 — FAVORITES,
// BUY NOW, MY ACCOUNT AND ADDRESSES
// ==========================================================

/*
============================================================
 HONEYBAIL CUSTOMER STOREFRONT
 ICE BLUE EDITION

 PART 4 OF 8

 FAVORITES
 BUY NOW
 MY ACCOUNT
 SAVED ADDRESSES
============================================================
*/


// ==========================================================
// 31. LOAD FAVORITES
// ==========================================================

async function loadFavorites() {
  if (!user) {
    favorites = [];

    renderFavorites();
    renderProducts();

    return;
  }

  const data = await req('favorites/');

  favorites = Array.isArray(data.favorites)
    ? data.favorites
    : [];

  renderFavorites();

  // Essential: refresh the product cards so the
  // favorite hearts reflect the saved server state.
  renderProducts();
}


// ==========================================================
// 32. RENDER FAVORITES
// ==========================================================

function renderFavorites() {
  const container = $('favorites');

  if (!container) {
    return;
  }

  const savedProducts = favorites
    .map(item => item.product || item)
    .filter(product => product && product.id != null);

  if (!savedProducts.length) {
    container.innerHTML = `
      <div class="card cart-empty">

        <h3>Your Favorites Are Empty ♡</h3>

        <p>
          Save products you love and find them here
          whenever you're ready to order.
        </p>

        <button
          type="button"
          class="primary"
          data-page="shop"
        >
          Explore Products
        </button>

      </div>
    `;

    return;
  }

  container.innerHTML = savedProducts.map(product => {
    const available = productStock(product);

    const soldOut =
      available < 1 ||
      product.is_active === false;

    return `
      <article class="product favorite-product">

        <div class="productimage">
          ${productImage(product)}
        </div>

        <div class="productbody">

          <span class="category">
            ${html(product.category || 'Sweet Treats')}
          </span>

          <h3>${html(product.name || 'Product')}</h3>

          <p class="price">
            ${peso(product.price)}
          </p>

          <p class="muted">
            ${soldOut
              ? 'Currently unavailable'
              : `${available} available`
            }
          </p>

          <div class="actions product-actions">

            <button
              type="button"
              class="primary"
              data-action="buy"
              data-id="${Number(product.id)}"
              ${soldOut ? 'disabled' : ''}
            >
              Buy Now
            </button>

            <button
              type="button"
              class="outline"
              data-action="add"
              data-id="${Number(product.id)}"
              ${soldOut ? 'disabled' : ''}
            >
              Add to Cart
            </button>

            <button
              type="button"
              class="favorite-button is-favorite"
              data-action="fav"
              data-id="${Number(product.id)}"
              aria-pressed="true"
              aria-label="Remove ${html(product.name)} from favorites"
              title="Remove from Favorites"
            >
              <span aria-hidden="true">♥</span>
              <span>Saved</span>
            </button>

          </div>

        </div>

      </article>
    `;
  }).join('');
}


// ==========================================================
// 33. ADD OR REMOVE FAVORITE
// ==========================================================

async function addFavorite(productId) {
  if (!user) {
    page('login');

    notify(
      'Please log in to save your favorite products.'
    );

    return;
  }

  const id = Number(productId);

  if (!Number.isInteger(id) || id < 1) {
    throw Error('Invalid product.');
  }

  // Refresh the saved state before deciding whether
  // this action adds or removes a favorite.
  await loadFavorites();

  const alreadySaved = isProductFavorited(id);

  if (alreadySaved) {
    await req(
      'favorites/',
      'DELETE',
      {
        product_id: id
      }
    );

    // Update only after the server confirms success.
    favorites = favorites.filter(item => {
      const product = item.product || item;

      return Number(product.id) !== id;
    });

    renderFavorites();
    renderProducts();

    notify('Removed from your favorites.');

  } else {
    await req(
      'favorites/',
      'POST',
      {
        product_id: id
      }
    );

    // Read the saved state back from Django.
    await loadFavorites();

    notify('Added to your favorites! ♥');
  }
}


// ==========================================================
// 34. BUY NOW
// ==========================================================

async function buyNow(productId) {
  if (!user) {
    page('login');

    notify(
      'Please log in before purchasing.'
    );

    return;
  }

  await loadProducts();

  const product = findProduct(productId);

  if (!product) {
    throw Error(
      'This product is no longer available.'
    );
  }

  if (
    product.is_active === false ||
    productStock(product) < 1
  ) {
    throw Error(
      'Sorry, this product is out of stock.'
    );
  }

  // Buy Now is a separate checkout mode.
  // It does not add another item to the cart.
  checkoutMode = 'buy';

  buyNowItem = {
    product,
    quantity: 1
  };

  await loadAddresses();

  renderCheckoutAddresses();
  renderCheckoutSummary();

  page('checkout');
}


// ==========================================================
// 35. LOAD MY ACCOUNT
// ==========================================================

async function loadAccount() {
  if (!user) {
    page('login');
    return;
  }

  // Refresh the customer's actual server-side profile.
  const data = await req('me/');

  user = data.customer || user;

  identity();

  const nameElement =
    $('profileName') || $('accountName');

  const emailElement =
    $('profileEmail') || $('accountEmail');

  if (nameElement) {
    nameElement.textContent =
      user.name ||
      user.full_name ||
      user.username ||
      'Customer';
  }

  if (emailElement) {
    emailElement.textContent =
      user.email || '—';
  }

  // Load this customer's saved delivery addresses.
  await loadAddresses();

  renderAccountAddresses();
}


// ==========================================================
// 36. LOAD SAVED ADDRESSES
// ==========================================================

async function loadAddresses() {
  if (!user) {
    addresses = [];
    selectedAddressId = null;

    return;
  }

  const data = await req('addresses/');

  addresses = Array.isArray(data.addresses)
    ? data.addresses
    : [];

  addressFeatureAvailable = true;

  const selectedAddress = addresses.find(
    item =>
      Number(item.id) === Number(selectedAddressId)
  );

  // Preserve a valid selection. Otherwise use the
  // default address, or the first saved address.
  if (!selectedAddress) {
    const defaultAddress = addresses.find(
      item => item.is_default
    );

    selectedAddressId = defaultAddress
      ? Number(defaultAddress.id)
      : addresses.length
        ? Number(addresses[0].id)
        : null;
  }
}


// ==========================================================
// 37. FORMAT DELIVERY ADDRESS
// ==========================================================

function formatAddress(address) {
  if (!address) {
    return '';
  }

  return [
    address.street,
    address.barangay,
    address.city,
    address.province,
    address.postal_code
  ]
    .filter(value =>
      value != null && String(value).trim() !== ''
    )
    .map(value => String(value).trim())
    .join(', ');
}


// ==========================================================
// 38. RENDER ACCOUNT ADDRESSES
// ==========================================================

function renderAccountAddresses() {
  const container =
    $('savedAddresses') || $('accountAddresses');

  if (!container) {
    return;
  }

  if (!addresses.length) {
    container.innerHTML = `
      <div class="card address-empty">

        <p>
          You haven't saved a delivery address yet.
        </p>

        <button
          type="button"
          class="primary"
          data-action="open-add-address"
        >
          + Add Delivery Address
        </button>

      </div>
    `;

    return;
  }

  container.innerHTML = addresses.map(address => `
    <article class="card address-card">

      <div class="address-card-header">

        <div>
          <strong>
            ${html(address.recipient || 'Recipient')}
          </strong>

          <span class="muted">
            ${html(address.label || 'Home')}
          </span>
        </div>

        ${address.is_default
          ? '<span class="category">Default</span>'
          : ''
        }

      </div>

      <p>${html(formatAddress(address))}</p>

      <p class="muted">
        ${html(address.phone || '')}
      </p>

      <div class="actions">

        <button
          type="button"
          class="outline"
          data-action="edit-address"
          data-id="${Number(address.id)}"
        >
          Edit
        </button>

        <button
          type="button"
          class="outline"
          data-action="delete-address"
          data-id="${Number(address.id)}"
        >
          Delete
        </button>

        ${!address.is_default ? `
          <button
            type="button"
            class="outline"
            data-action="default-address"
            data-id="${Number(address.id)}"
          >
            Set as Default
          </button>
        ` : ''}

      </div>

    </article>
  `).join('');
}


// ==========================================================
// 39. RENDER CHECKOUT ADDRESSES
// ==========================================================

function renderCheckoutAddresses() {
  const container = $('checkoutAddresses');

  if (!container) {
    return;
  }

  if (!addresses.length) {
    container.innerHTML = `
      <div class="card address-empty">

        <p>
          Add a delivery address before placing your order.
        </p>

        <button
          type="button"
          class="primary"
          data-action="open-add-address"
        >
          + Add Delivery Address
        </button>

      </div>
    `;

  } else {
    container.innerHTML = addresses.map(address => `
      <label class="card checkout-address-option">

        <input
          type="radio"
          name="selectedAddress"
          value="${Number(address.id)}"
          ${Number(address.id) === Number(selectedAddressId)
            ? 'checked'
            : ''
          }
        >

        <span class="checkout-address-details">

          <strong>
            ${html(address.recipient || 'Recipient')}
          </strong>

          <span class="muted">
            ${html(address.label || 'Home')}
            ${address.is_default ? ' · Default' : ''}
          </span>

          <span>${html(formatAddress(address))}</span>

          <span class="muted">
            ${html(address.phone || '')}
          </span>

        </span>

      </label>
    `).join('') + `
      
    `;
  }

  // Use the existing confirmation checkbox from HTML.
  // Do not generate a second element with the same ID.
  const confirmation = $('confirmAddress');

  if (confirmation) {
    confirmation.checked = false;
  }

  container.querySelectorAll(
    'input[name="selectedAddress"]'
  ).forEach(input => {
    input.addEventListener('change', () => {
      selectedAddressId = Number(input.value);

      if (confirmation) {
        confirmation.checked = false;
      }
    });
  });
}


// ==========================================================
// 40. SELECT DELIVERY ADDRESS
// ==========================================================

function selectDeliveryAddress(addressId) {
  const id = Number(addressId);

  const address = addresses.find(
    item => Number(item.id) === id
  );

  if (!address) {
    notify('Please select a valid delivery address.');
    return;
  }

  selectedAddressId = id;

  renderCheckoutAddresses();
}


// ==========================================================
// 41. OPEN ADDRESS FORM
// ==========================================================

function openAddressForm(addressId = null) {
  if (!user) {
    page('login');
    return;
  }

  // Preserve the page the customer should return to.
  if (
    $('checkoutPage') &&
    !$('checkoutPage').hidden
  ) {
    addressReturnPage = 'checkout';
  } else if (
    !$('addressPage') ||
    $('addressPage').hidden
  ) {
    addressReturnPage = 'account';
  }

  const form = $('addressForm');

  if (!form) {
    notify('Address form not found in store.html.');
    return;
  }

  form.reset();

  const idInput = $('addressId');
  const title = $('addressFormTitle');

  if (idInput) {
    idInput.value = '';
  }

  if (title) {
    title.textContent = 'Add Delivery Address';
  }

  if (addressId !== null) {
    const address = addresses.find(
      item => Number(item.id) === Number(addressId)
    );

    if (!address) {
      notify('Address not found.');
      return;
    }

    if (title) {
      title.textContent = 'Edit Delivery Address';
    }

    if (idInput) {
      idInput.value = address.id;
    }

    // Match the actual form field names in the
    // storefront address form.
    for (const field of [
      'label',
      'recipient',
      'phone',
      'street',
      'barangay',
      'city',
      'province',
      'postal_code'
    ]) {
      if (form.elements[field]) {
        form.elements[field].value =
          address[field] || '';
      }
    }

    if (form.elements.is_default) {
      form.elements.is_default.checked =
        Boolean(address.is_default);
    }
  }

  page('address');
}


// ==========================================================
// 42. SAVE ADDRESS
// ==========================================================

async function saveAddress(event) {
  event.preventDefault();

  if (!user) {
    page('login');
    return;
  }

  const form = event.currentTarget || event.target;

  if (!form.reportValidity()) {
    return;
  }

  const data = Object.fromEntries(
    new FormData(form)
  );

  const addressId =
    data.address_id ||
    data.id ||
    $('addressId')?.value ||
    '';

  // These field names match the Django address view.
  const payload = {
    label: String(data.label || 'Home').trim(),
    recipient: String(data.recipient || '').trim(),
    phone: String(data.phone || '').trim(),
    street: String(data.street || '').trim(),
    barangay: String(data.barangay || '').trim(),
    city: String(data.city || '').trim(),
    province: String(data.province || '').trim(),
    postal_code: String(data.postal_code || '').trim(),
    is_default: data.is_default === 'on'
  };

  if (addressId) {
    await req(
      'addresses/',
      'PATCH',
      {
        address_id: Number(addressId),
        ...payload
      }
    );
  } else {
    await req(
      'addresses/',
      'POST',
      payload
    );
  }

  await loadAddresses();

  renderAccountAddresses();
  renderCheckoutAddresses();

  page(addressReturnPage);

  notify(
    addressId
      ? 'Delivery address updated successfully.'
      : 'Delivery address saved successfully.'
  );
}


// ==========================================================
// 43. DELETE ADDRESS
// ==========================================================

async function deleteAddress(addressId) {
  const id = Number(addressId);

  const address = addresses.find(
    item => Number(item.id) === id
  );

  if (!address) {
    notify('Address not found.');
    return;
  }

  if (!window.confirm(
    'Are you sure you want to delete this delivery address?'
  )) {
    return;
  }

  // The backend expects address_id in the JSON body.
  await req(
    'addresses/',
    'DELETE',
    {
      address_id: id
    }
  );

  if (Number(selectedAddressId) === id) {
    selectedAddressId = null;
  }

  await loadAddresses();

  renderAccountAddresses();
  renderCheckoutAddresses();

  notify('Delivery address deleted.');
}


// ==========================================================
// 44. SET DEFAULT ADDRESS
// ==========================================================

async function setDefaultAddress(addressId) {
  const id = Number(addressId);

  const address = addresses.find(
    item => Number(item.id) === id
  );

  if (!address) {
    notify('Address not found.');
    return;
  }

  await req(
    'addresses/',
    'PATCH',
    {
      address_id: id,
      is_default: true
    }
  );

  await loadAddresses();

  renderAccountAddresses();
  renderCheckoutAddresses();

  notify('Default delivery address updated.');
}


// ==========================================================
// END OF PART 4 OF 8
//
// NEXT: PART 5 — CHECKOUT AND ORDER SUBMISSION
// ==========================================================

/*
============================================================
 HONEYBAIL CUSTOMER STOREFRONT
 ICE BLUE EDITION

 PART 5 OF 8

 CHECKOUT
 SHIPPING CALCULATION
 STOCK VALIDATION
 ORDER SUBMISSION
============================================================
*/


// ==========================================================
// 45. GET CHECKOUT ITEMS
// ==========================================================

function checkoutItems() {
  if (checkoutMode === 'buy') {
    if (!buyNowItem) {
      return [];
    }

    return [{
      product: buyNowItem.product,
      quantity: Number(buyNowItem.quantity)
    }];
  }

  return selectedCartItems().map(item => ({
    product: item.product,
    quantity: Number(item.quantity),
    cart_item_id: Number(item.id)
  }));
}


// ==========================================================
// 46. CHECKOUT QUANTITY
// ==========================================================

function checkoutQuantity() {
  return checkoutItems().reduce(
    (sum, item) => sum + Number(item.quantity),
    0
  );
}


// ==========================================================
// 47. CHECKOUT SUBTOTAL
// ==========================================================

function checkoutSubtotal() {
  return checkoutItems().reduce(
    (sum, item) =>
      sum +
      Number(item.product.price || 0) *
      Number(item.quantity),
    0
  );
}


// ==========================================================
// 48. CHECKOUT DELIVERY FEE
// ==========================================================

function checkoutDeliveryFee() {
  return calculateDeliveryFee(
    checkoutQuantity()
  );
}


// ==========================================================
// 49. CHECKOUT GRAND TOTAL
// ==========================================================

function checkoutGrandTotal() {
  return (
    checkoutSubtotal() +
    checkoutDeliveryFee()
  );
}


// ==========================================================
// 50. RENDER CHECKOUT SUMMARY
// ==========================================================

function renderCheckoutSummary() {
  const container = $('checkoutItems');

  if (!container) {
    return;
  }

  const items = checkoutItems();

  container.innerHTML = items.length
    ? items.map(item => `
        <div class="cartrow checkout-item">

          <div class="cart-product">

            <div class="cart-thumbnail">
              ${productImage(item.product)}
            </div>

            <div class="cart-details">

              <strong>
                ${html(item.product.name || 'Product')}
              </strong>

              <p class="muted">
                ${peso(item.product.price)} each
              </p>

              <p class="muted">
                Quantity: ${Number(item.quantity)}
              </p>

            </div>

          </div>

          <strong>
            ${peso(
              Number(item.product.price || 0) *
              Number(item.quantity)
            )}
          </strong>

        </div>
      `).join('')

    : `
        <div class="card cart-empty">
          <p>No products selected for checkout.</p>
        </div>
      `;

  const subtotalElement = $('checkoutSubtotal');
  const deliveryElement = $('checkoutDeliveryFee');
  const totalElement = $('checkoutTotal');
  const quantityElement = $('checkoutQuantity');

  if (subtotalElement) {
    subtotalElement.textContent =
      peso(checkoutSubtotal());
  }

  if (deliveryElement) {
    deliveryElement.textContent =
      peso(checkoutDeliveryFee());
  }

  if (totalElement) {
    totalElement.textContent =
      peso(checkoutGrandTotal());
  }

  if (quantityElement) {
    quantityElement.textContent =
      `${checkoutQuantity()} item(s)`;
  }

  const submitButton = $('placeOrderBtn');

  if (submitButton) {
    const invalidItem = items.some(item => {
      const quantity = Number(item.quantity);
      const stock = productStock(item.product);

      return (
        item.product?.is_active === false ||
        stock < 1 ||
        !Number.isInteger(quantity) ||
        quantity < 1 ||
        quantity > stock
      );
    });

    submitButton.disabled =
      !CHECKOUT_BACKEND_READY ||
      !items.length ||
      invalidItem ||
      submittingOrder;

    submitButton.textContent = submittingOrder
      ? 'Placing Order...'
      : invalidItem
        ? 'Stock Unavailable'
        : 'Confirm & Place Order';
  }
}


// ==========================================================
// 51. LOAD CHECKOUT
// ==========================================================

async function loadCheckout() {
  if (!user) {
    page('login');
    return;
  }

  if (checkoutMode === 'cart') {
    await loadCart();
  }

  await loadProducts();

  if (checkoutMode === 'buy' && buyNowItem) {
    const currentProduct = findProduct(
      buyNowItem.product.id
    );

    if (!currentProduct) {
      buyNowItem = null;
    } else {
      buyNowItem.product = currentProduct;
    }
  }

  await loadAddresses();

  renderCheckoutAddresses();
  renderCheckoutSummary();

  const backButton = $('checkoutBack');

  if (backButton) {
    backButton.textContent =
      checkoutMode === 'buy'
        ? '← Back to Shop'
        : '← Back to Cart';
  }
}


// ==========================================================
// 52. VALIDATE CHECKOUT ITEMS
// ==========================================================

async function validateCheckoutStock() {
  await loadProducts();

  if (checkoutMode === 'buy' && buyNowItem) {
    const currentProduct = findProduct(
      buyNowItem.product.id
    );

    if (!currentProduct) {
      throw Error(
        'This product is no longer available.'
      );
    }

    buyNowItem.product = currentProduct;
  }

  if (checkoutMode === 'cart') {
    await loadCart();
  }

  const items = checkoutItems();

  if (!items.length) {
    throw Error(
      'Please select at least one product to check out.'
    );
  }

  for (const item of items) {
    const product = item.product;
    const quantity = Number(item.quantity);
    const stock = productStock(product);

    if (
      product?.is_active === false ||
      stock < 1
    ) {
      throw Error(
        `${product?.name || 'A product'} is out of stock.`
      );
    }

    if (
      !Number.isInteger(quantity) ||
      quantity < 1 ||
      quantity > stock
    ) {
      throw Error(
        `Insufficient stock for ${product.name}.`
      );
    }
  }

  return items;
}


// ==========================================================
// 53. SUBMIT CHECKOUT
// ==========================================================

async function submitCheckout(event) {
  event.preventDefault();

  if (submittingOrder) {
    return;
  }

  if (!user) {
    page('login');
    return;
  }

  submittingOrder = true;
  renderCheckoutSummary();

  try {
    if (savingCartItemIds.size > 0) {
      throw Error(
        'Please wait until your cart changes finish saving.'
      );
    }

    const form = $('checkoutForm');

    if (!form) {
      throw Error(
        'Checkout form not found in store.html.'
      );
    }

    if (!form.reportValidity()) {
      return;
    }

    const formData = Object.fromEntries(
      new FormData(form)
    );

    // This storefront currently supports COD only.
    if (
      formData.payment_method &&
      formData.payment_method !== 'COD'
    ) {
      throw Error(
        'Cash on Delivery is the only supported payment method.'
      );
    }

    // Verify the order-policy checkbox if present.
    const policyCheckbox = $('orderPolicy');

    if (
      policyCheckbox &&
      !policyCheckbox.checked
    ) {
      throw Error(
        'Please accept the order policy before placing your order.'
      );
    }

    await loadAddresses();

    const address = addresses.find(
      item =>
        Number(item.id) === Number(selectedAddressId)
    );

    if (!address) {
      throw Error(
        'Please select a saved delivery address.'
      );
    }

    const confirmation = $('confirmAddress');

    if (!confirmation || !confirmation.checked) {
      throw Error(
        'Please confirm your delivery address.'
      );
    }

    const items = await validateCheckoutStock();

    // These are the customer and delivery details.
    // Django must calculate the authoritative total.
    const orderPayload = {
      address_id: Number(address.id),
      payment_method: 'COD',
      notes: formData.notes || '',
      policy_accepted: true
    };

    if (checkoutMode === 'buy') {
      if (!buyNowItem) {
        throw Error(
          'Please select a product to purchase.'
        );
      }

      orderPayload.buy_now = {
        product_id: Number(buyNowItem.product.id),
        quantity: Number(buyNowItem.quantity)
      };

    } else {
      const selectedIds = items.map(
        item => Number(item.cart_item_id)
      );

      if (
        !selectedIds.length ||
        selectedIds.some(
          id => !Number.isInteger(id) || id < 1
        )
      ) {
        throw Error(
          'No valid cart items were selected.'
        );
      }

      orderPayload.selected_cart_item_ids =
        selectedIds;
    }

    // Submit to the actual Django endpoint.
    const result = await req(
      'orders/',
      'POST',
      orderPayload
    );

    // Do not reset the cart or checkout until Django
    // confirms that the order was successfully created.
    checkoutMode = 'cart';
    buyNowItem = null;

    selectedCartItemIds.clear();
    cartSelectionInitialized = false;

    form.reset();

    await loadCart();

    page('orders');

    // The backend may use either order_id or id.
    const orderNumber =
      result.order_id ?? result.id ?? 'New';

    const orderTotal = Number(
      result.total ??
      result.grand_total ??
      checkoutGrandTotal()
    );

    notify(
      `Order #${orderNumber} placed successfully! ` +
      `Total: ${peso(orderTotal)}. ` +
      'Payment: Cash on Delivery.'
    );

    await loadOrders();

  } finally {
    submittingOrder = false;
    renderCheckoutSummary();
  }
}


// ==========================================================
// END OF PART 5 OF 8
//
// NEXT: PART 6 — ORDER HISTORY,
// TRACKING AND PRODUCT REVIEWS
// ==========================================================

/*
============================================================
 HONEYBAIL CUSTOMER STOREFRONT
 ICE BLUE EDITION

 PART 6 OF 8

 ORDER HISTORY
 ORDER TRACKING
 CUSTOMER REVIEWS
============================================================
*/


// ==========================================================
// 54. ORDER STATUS CONFIGURATION
// ==========================================================

// These statuses reflect the customer order status
// returned by the Django backend.

const ORDER_STEPS = [
  'Pending',
  'Processing',
  'Shipped',
  'Delivered'
];

const ORDER_STATUS_PROGRESS = {
  'Pending': 0,
  'Processing': 1,
  'Shipped': 2,
  'Delivered': 3
};


// ==========================================================
// 55. RENDER ORDER TRACKING
// ==========================================================

function orderTracking(status) {
  const currentStatus = String(status || 'Pending');

  if (
    currentStatus === 'Cancelled' ||
    currentStatus === 'Canceled'
  ) {
    return `
      <div class="order-tracking cancelled">

        <strong>Order Cancelled</strong>

        <p class="muted">
          Please contact the store if you need assistance.
        </p>

      </div>
    `;
  }

  const currentIndex =
    ORDER_STATUS_PROGRESS[currentStatus] ?? -1;

  return `
    <div class="order-tracking">

      ${ORDER_STEPS.map((step, index) => `
        <div class="tracking-step ${
          currentIndex >= index ? 'completed' : ''
        }">

          <span class="tracking-icon">
            ${currentIndex >= index ? '✓' : '○'}
          </span>

          <span>${html(step)}</span>

        </div>
      `).join('')}

    </div>

    <p class="muted order-current-status">
      Current status: ${html(currentStatus)}
    </p>
  `;
}


// ==========================================================
// 56. LOAD CUSTOMER ORDERS
// ==========================================================

async function loadOrders() {
  if (!user) {
    page('login');

    notify('Please log in to view your orders.');

    return;
  }

  const data = await req('orders/');

  const orders = Array.isArray(data.orders)
    ? data.orders
    : [];

  const container = $('orders');

  if (!container) {
    console.warn(
      'Order list container #orders was not found.'
    );

    return;
  }

  if (!orders.length) {
    container.innerHTML = `
      <div class="card cart-empty">

        <h3>No orders yet</h3>

        <p>
          Your purchases will appear here
          after you place your first order.
        </p>

        <button
          type="button"
          class="primary"
          data-page="shop"
        >
          Start Shopping
        </button>

      </div>
    `;

    return;
  }

  container.innerHTML = orders.map(order => {
    const orderId = Number(order.id);

    const status = String(order.status || 'Pending');

    const subtotal = Number(order.subtotal || 0);
    const deliveryFee = Number(order.delivery_fee || 0);
    const total = Number(order.total || 0);

    const items = Array.isArray(order.items)
      ? order.items
      : [];

    const delivered = status === 'Delivered';

    return `
      <article class="card order-card">

        <div class="order-header">

          <div>
            <h3>Order #${orderId}</h3>

            <p class="muted">
              ${html(order.date || '')}
            </p>
          </div>

          <div class="order-header-total">

            <strong>${peso(total)}</strong>

            <p>${html(status)}</p>

            <p class="muted">
              ${html(order.payment_method || 'COD')}
              · ${html(order.payment_status || 'Unpaid')}
            </p>

          </div>

        </div>

        ${orderTracking(status)}

        <div class="order-delivery-details">

          <h4>Delivery Details</h4>

          <p>
            <strong>${html(order.recipient || '')}</strong>
          </p>

          <p>${html(order.phone || '')}</p>

          <p>${html(order.address || '')}</p>

        </div>

        <div class="order-products">

          ${items.map(item => {
            const productId = Number(item.product_id || 0);
            const name = item.name || 'Product';
            const quantity = Number(item.quantity || 0);
            const price = Number(item.price || 0);
            const itemSubtotal = Number(
              item.subtotal ?? price * quantity
            );

            return `
              <div class="orderrow">

                <div class="order-item-info">

                  <strong>
                    ${html(name)}
                  </strong>

                  <p class="muted">
                    ${peso(price)} × ${quantity}
                  </p>

                </div>

                <div class="order-item-actions">

                  <strong>${peso(itemSubtotal)}</strong>

                  ${delivered && productId > 0 ? `
                    <button
                      type="button"
                      class="outline"
                      data-action="write-review"
                      data-id="${productId}"
                    >
                      Write Review
                    </button>
                  ` : ''}

                </div>

              </div>
            `;
          }).join('')}

        </div>

        <div class="checkout-totals">

          <p>
            <span>Subtotal</span>
            <strong>${peso(subtotal)}</strong>
          </p>

          <p>
            <span>Delivery Fee</span>
            <strong>${peso(deliveryFee)}</strong>
          </p>

          <h3>
            <span>Grand Total</span>
            <strong>${peso(total)}</strong>
          </h3>

        </div>

        ${order.notes ? `
          <p class="muted">
            Order notes: ${html(order.notes)}
          </p>
        ` : ''}

      </article>
    `;
  }).join('');
}


// ==========================================================
// 57. LOAD PRODUCT REVIEWS
// ==========================================================

async function loadReviews(productId) {
  const id = Number(productId);

  if (!Number.isInteger(id) || id < 1) {
    throw Error('Please select a valid product.');
  }

  reviewProduct = id;

  const product = findProduct(id);

  const title = $('reviewTitle');

  if (title) {
    title.textContent =
      `${product?.name || 'Product'} — Customer Reviews`;
  }

  // GET reviews is public in the Django backend.
  const data = await req(`reviews/${id}/`);

  const reviews = Array.isArray(data.reviews)
    ? data.reviews
    : [];

  const summary = $('reviewSummary');

  if (summary) {
    if (reviews.length) {
      const average = reviews.reduce(
        (sum, review) =>
          sum + Number(review.rating || 0),
        0
      ) / reviews.length;

      summary.textContent =
        `${reviews.length} review(s) · ` +
        `Average rating: ${average.toFixed(1)} / 5`;
    } else {
      summary.textContent = 'No customer reviews yet.';
    }
  }

  const container = $('reviews');

  if (!container) {
    throw Error('Review list container was not found.');
  }

  container.innerHTML = reviews.length
    ? reviews.map(review => {
        const rating = Math.max(
          0,
          Math.min(
            5,
            Math.floor(Number(review.rating) || 0)
          )
        );

        return `
          <article class="card review-card">

            <div class="review-header">

              <strong>
                ${html(review.name || 'Customer')}
              </strong>

              <span class="muted">
                ${html(review.date || '')}
              </span>

            </div>

            <p class="price review-stars"
               aria-label="${rating} out of 5 stars">

              ${'★'.repeat(rating)}${'☆'.repeat(5 - rating)}

            </p>

            <p>
              ${html(review.comment || '')}
            </p>

            ${review.mine ? `
              <span class="category">Your Review</span>
            ` : ''}

          </article>
        `;
      }).join('')

    : `
      <div class="card">
        No customer reviews yet. Be the first to share
        your experience after receiving your order.
      </div>
    `;

  page('review');
}


// ==========================================================
// 58. OPEN WRITE REVIEW PAGE
// ==========================================================

function openWriteReview(productId) {
  if (!user) {
    page('login');

    notify('Please log in to write a review.');

    return;
  }

  const id = Number(productId);

  if (!Number.isInteger(id) || id < 1) {
    notify('Please select a valid product.');

    return;
  }

  reviewProduct = id;

  const product = findProduct(id);

  const nameElement = $('writeReviewProductName');

  if (nameElement) {
    nameElement.textContent =
      product?.name || 'Product Review';
  }

  const form = $('reviewForm');

  if (form) {
    form.reset();
  }

  page('writeReview');
}


// ==========================================================
// 59. SUBMIT PRODUCT REVIEW
// ==========================================================

async function submitReview(event) {
  event.preventDefault();

  if (!user) {
    page('login');

    notify('Please log in to submit a review.');

    return;
  }

  if (!reviewProduct) {
    throw Error('Please select a product to review.');
  }

  const form = event.currentTarget || event.target;

  if (!form.reportValidity()) {
    return;
  }

  const formData = Object.fromEntries(
    new FormData(form)
  );

  const rating = Number(formData.rating);

  const comment = String(
    formData.comment || ''
  ).trim();

  if (
    !Number.isInteger(rating) ||
    rating < 1 ||
    rating > 5
  ) {
    throw Error('Please choose a rating from 1 to 5.');
  }

  if (!comment) {
    throw Error('Please enter your review.');
  }

  const productId = reviewProduct;

  // Django verifies that this customer has a delivered
  // order containing the product before saving the review.
  await req(
    `reviews/${productId}/`,
    'POST',
    {
      rating,
      comment
    }
  );

  form.reset();

  await loadProducts();

  await loadReviews(productId);

  notify('Your review has been submitted successfully! ♡');
}


// ==========================================================
// 60. DELETE MY PRODUCT REVIEW
// ==========================================================

async function deleteReview() {
  if (!user) {
    page('login');

    notify('Please log in to manage your review.');

    return;
  }

  if (!reviewProduct) {
    notify('Please select a product first.');

    return;
  }

  if (!window.confirm(
    'Delete your review for this product?'
  )) {
    return;
  }

  const productId = reviewProduct;

  await req(
    `reviews/${productId}/`,
    'DELETE',
    {}
  );

  await loadProducts();

  await loadReviews(productId);

  notify('Your review has been deleted.');
}


// ==========================================================
// END OF PART 6 OF 8
//
// NEXT: PART 7 — LOGIN, REGISTRATION,
// LOGOUT AND EVENT HANDLERS
// ==========================================================

/*
============================================================
 HONEYBAIL CUSTOMER STOREFRONT
 ICE BLUE EDITION

 PART 7 OF 8

 AUTHENTICATION
 EVENT HANDLERS
 ADDRESS FORMS
 CHECKOUT
 REVIEWS
============================================================
*/


// ==========================================================
// 61. LOGOUT CONFIRMATION
// ==========================================================

function showLogoutConfirmation() {
  const dialog = $('logoutDialog');

  if (dialog && typeof dialog.showModal === 'function') {
    if (!dialog.open) {
      dialog.showModal();
    }

    return;
  }

  if (window.confirm('Are you sure you want to log out?')) {
    act(confirmLogout);
  }
}


// ==========================================================
// 62. CONFIRM CUSTOMER LOGOUT
// ==========================================================

async function confirmLogout() {
  await req('logout/', 'POST', {});

  // Clear local customer data after successful logout.
  user = null;
  cart = [];
  favorites = [];
  addresses = [];

  reviewProduct = null;
  selectedAddressId = null;

  checkoutMode = 'cart';
  buyNowItem = null;

  submittingOrder = false;

  selectedCartItemIds.clear();
  cartSelectionInitialized = false;
  savingCartItemIds.clear();

  updateCartCount();
  renderCart();
  renderFavorites();
  renderProducts();
  renderAccountAddresses();
  identity();

  const dialog = $('logoutDialog');

  if (dialog?.open) {
    dialog.close();
  }

  page('shop');

  notify('You have logged out of Honeybail. See you again! ♡');
}


// ==========================================================
// 63. CENTRAL BUTTON EVENT HANDLER
// ==========================================================

// Handles static buttons and buttons created dynamically
// inside product cards, Favorites, Cart, and addresses.

document.addEventListener('click', event => {
  const button = event.target.closest(
    'button[data-page], button[data-action]'
  );

  if (!button || button.disabled) {
    return;
  }

  // Navigation buttons.
  if (button.dataset.page) {
    event.preventDefault();

    page(button.dataset.page);

    return;
  }

  const action = button.dataset.action;
  const id = Number(button.dataset.id);

  event.preventDefault();

  act(async () => {
    switch (action) {

      // SHOPPING

      case 'add':
        await addToCart(id);
        break;

      case 'buy':
        await buyNow(id);
        break;

      case 'fav':
        await addFavorite(id);
        break;

      case 'reviews':
        await loadReviews(id);
        break;


      // CART

      case 'qty-minus':
        await changeCartQuantity(id, -1);
        break;

      case 'qty-plus':
        await changeCartQuantity(id, 1);
        break;

      case 'remove':
        await removeCartItem(id);
        break;


      // SAVED ADDRESSES

      case 'select-address':
        selectDeliveryAddress(id);
        break;

      case 'edit-address':
        openAddressForm(id);
        break;

      case 'open-add-address':
        openAddressForm();
        break;

      case 'delete-address':
        await deleteAddress(id);
        break;

      case 'default-address':
        await setDefaultAddress(id);
        break;


      // REVIEWS

      case 'write-review':
        openWriteReview(id);
        break;

      default:
        console.warn(
          'Unknown Honeybail action:',
          action
        );
    }
  });
});


// ==========================================================
// 64. CART CHECKBOX EVENTS
// ==========================================================

document.addEventListener('change', event => {
  const target = event.target;

  if (target.id === 'selectAllCart') {
    toggleSelectAllCart(target.checked);
    return;
  }

  if (target.classList.contains('cart-item-checkbox')) {
    toggleCartItemSelection(
      Number(target.dataset.id),
      target.checked
    );
  }
});


// ==========================================================
// 65. LOGIN FORM
// ==========================================================

const loginForm = $('loginForm');

if (loginForm) {
  loginForm.addEventListener('submit', event => {
    event.preventDefault();

    act(async () => {
      const form = event.currentTarget;

      if (!form.reportValidity()) {
        return;
      }

      const formData = Object.fromEntries(
        new FormData(form)
      );

      // Django expects email and password.
      await req('login/', 'POST', {
        email: formData.email,
        password: formData.password
      });

      await session();

      if (!user) {
        throw Error(
          'Login response received, but the customer session could not be restored.'
        );
      }

      // Load data belonging to this customer.
      cart = [];
      favorites = [];
      addresses = [];

      selectedAddressId = null;

      selectedCartItemIds.clear();
      cartSelectionInitialized = false;
      savingCartItemIds.clear();

      await Promise.all([
        loadCart(),
        loadFavorites(),
        loadAddresses()
      ]);

      renderAccountAddresses();
      identity();

      form.reset();

      page('shop');

      notify('Welcome back to Honeybail! ♡');
    });
  });
}


// ==========================================================
// 66. REGISTRATION FORM
// ==========================================================

const registerForm = $('registerForm');

if (registerForm) {
  registerForm.addEventListener('submit', event => {
    event.preventDefault();

    act(async () => {
      const form = event.currentTarget;

      if (!form.reportValidity()) {
        return;
      }

      const formData = Object.fromEntries(
        new FormData(form)
      );

      if (formData.password !== formData.confirm) {
        throw Error('Your passwords do not match.');
      }

      // The backend expects name, email, and password.
      await req('register/', 'POST', {
        name: formData.name,
        email: formData.email,
        password: formData.password
      });

      await session();

      if (!user) {
        throw Error(
          'Registration completed, but the customer session could not be restored.'
        );
      }

      cart = [];
      favorites = [];
      addresses = [];

      selectedAddressId = null;

      selectedCartItemIds.clear();
      cartSelectionInitialized = false;
      savingCartItemIds.clear();

      await Promise.all([
        loadCart(),
        loadFavorites(),
        loadAddresses()
      ]);

      renderAccountAddresses();
      identity();

      form.reset();

      page('shop');

      notify('Welcome to Honeybail! Your account is ready. ♡');
    });
  });
}


// ==========================================================
// 67. SHARED BUTTON BINDING HELPER
// ==========================================================

function bindClick(id, callback) {
  const element = $(id);

  if (!element) {
    // Some optional controls may not exist in every page.
    return;
  }

  element.addEventListener('click', event => {
    event.preventDefault();

    act(callback);
  });
}


// ==========================================================
// 68. LOGOUT BUTTON
// ==========================================================

bindClick('logout', showLogoutConfirmation);


// ==========================================================
// 69. CANCEL LOGOUT
// ==========================================================

bindClick('cancelLogout', () => {
  const dialog = $('logoutDialog');

  if (dialog?.open) {
    dialog.close();
  }
});


// ==========================================================
// 70. CONFIRM LOGOUT
// ==========================================================

bindClick('confirmLogout', confirmLogout);


// ==========================================================
// 71. REFRESH PRODUCT CATALOG
// ==========================================================

bindClick('refresh', loadProducts);


// ==========================================================
// 72. START CART CHECKOUT
// ==========================================================

bindClick('checkoutStart', startCartCheckout);


// ==========================================================
// 73. RETURN FROM CHECKOUT
// ==========================================================

bindClick('checkoutBack', () => {
  page(checkoutMode === 'buy' ? 'shop' : 'cart');
});


// ==========================================================
// 74. ADD ADDRESS BUTTON
// ==========================================================

bindClick('addAddressBtn', () => {
  openAddressForm();
});


// ==========================================================
// 75. CHECKOUT ADD ADDRESS BUTTON
// ==========================================================

bindClick('checkoutAddAddress', () => {
  openAddressForm();
});


// ==========================================================
// 76. CANCEL ADDRESS FORM
// ==========================================================

bindClick('cancelAddressBtn', () => {
  page(addressReturnPage);
});


// ==========================================================
// 77. SAVE ADDRESS FORM
// ==========================================================

const addressForm = $('addressForm');

if (addressForm) {
  addressForm.addEventListener('submit', event => {
    event.preventDefault();

    act(() => saveAddress(event));
  });
}


// ==========================================================
// 78. SUBMIT CHECKOUT FORM
// ==========================================================

const checkoutForm = $('checkoutForm');

if (checkoutForm) {
  checkoutForm.addEventListener('submit', event => {
    event.preventDefault();

    act(() => submitCheckout(event));
  });
}


// ==========================================================
// 79. SUBMIT REVIEW FORM
// ==========================================================

const reviewForm = $('reviewForm');

if (reviewForm) {
  reviewForm.addEventListener('submit', event => {
    event.preventDefault();

    act(() => submitReview(event));
  });
}


// ==========================================================
// 80. DELETE REVIEW BUTTON
// ==========================================================

bindClick('deleteReview', deleteReview);


// ==========================================================
// END OF PART 7 OF 8
//
// NEXT: PART 8 — INITIALIZATION AND STARTUP
// ==========================================================
  
/*
============================================================
 HONEYBAIL CUSTOMER STOREFRONT
 ICE BLUE EDITION

 PART 8 OF 8

 CART CHECKOUT
 STOREFRONT INITIALIZATION
 APPLICATION STARTUP
============================================================
*/


// ==========================================================
// 81. START CHECKOUT FOR SELECTED CART ITEMS
// ==========================================================

async function startCartCheckout() {
  if (!user) {
    page('login');
    notify('Please log in before checking out.');
    return;
  }

  if (savingCartItemIds.size > 0) {
    notify('Please wait while your cart updates are saved.');
    return;
  }

  // Refresh cart data from Django before checkout.
  await loadCart();

  if (savingCartItemIds.size > 0) {
    notify('Please wait while your cart updates are saved.');
    return;
  }

  const items = selectedCartItems();

  if (!items.length) {
    notify('Please select at least one available product.');
    return;
  }

  for (const item of items) {
    const stock = productStock(item.product);
    const quantity = Number(item.quantity);

    if (
      item.product?.is_active === false ||
      stock < 1
    ) {
      notify(
        `${item.product?.name || 'A product'} is unavailable.`
      );
      return;
    }

    if (
      !Number.isInteger(quantity) ||
      quantity < 1 ||
      quantity > stock
    ) {
      notify(
        `Please check the quantity for ${item.product.name}.`
      );
      return;
    }
  }

  checkoutMode = 'cart';
  buyNowItem = null;

  page('checkout');
}


// ==========================================================
// 82. REFRESH STOREFRONT DATA
// ==========================================================

async function refreshStorefront() {
  // Restore the current Django customer session.
  await session();

  // Load the public product catalog.
  await loadProducts();

  if (user) {
    // Load only the signed-in customer's data.
    await Promise.all([
      loadCart(),
      loadFavorites(),
      loadAddresses()
    ]);

    renderCart();
    renderFavorites();
    renderProducts();
    renderAccountAddresses();
    updateCartCount();

  } else {
    // Clear customer-specific state for guests.
    cart = [];
    favorites = [];
    addresses = [];

    selectedAddressId = null;

    selectedCartItemIds.clear();
    cartSelectionInitialized = false;

    renderCart();
    renderFavorites();
    renderProducts();
    updateCartCount();
  }

  identity();
}


// ==========================================================
// 83. INITIALIZE STOREFRONT
// ==========================================================

async function initializeStorefront() {
  console.info(
    'Honeybail storefront initializing...'
  );

  try {
    await refreshStorefront();

    // Start on the Shop page.
    page('shop');

    console.info(
      'Honeybail storefront initialized successfully.'
    );

  } catch (error) {
    console.error(
      'Honeybail startup error:',
      error
    );

    notify(
      'Some storefront data could not be loaded. ' +
      'Check the Django server and browser console.'
    );
  }
}


// ==========================================================
// 84. PREVENT DUPLICATE INITIALIZATION
// ==========================================================

let honeybailInitialized = false;

function startHoneybail() {
  if (honeybailInitialized) {
    return;
  }

  honeybailInitialized = true;

  initializeStorefront();
}


// ==========================================================
// 85. START APPLICATION
// ==========================================================

// Supports a script loaded with defer or one loaded
// after the HTML document has finished parsing.

if (document.readyState === 'loading') {
  document.addEventListener(
    'DOMContentLoaded',
    startHoneybail,
    { once: true }
  );
} else {
  startHoneybail();
}


// ==========================================================
// END OF PART 8 OF 8
//
// HONEYBAIL STOREFRONT JAVASCRIPT COMPLETE
// ==========================================================
