const API_URL = "http://127.0.0.1:8000/api/products/";

function showPage(page) {
  const content = document.getElementById("content");

  const pages = {
    dashboard: `
      <h1>Welcome back, Admin!</h1>
      <p>Manage your store today.</p>
      <h3>Total Orders: 24</h3>
      <h3>Total Sales: ₱1,560</h3>
    `,

    orders: `
      <h1>Orders</h1>
      <p>Manage customer orders.</p>
      <button onclick="alert('Order management will be connected next.')">
        View Order
      </button>
    `,

    products: `
      <h1>Products</h1>
      <p>Products loaded from the Django database.</p>
      <button onclick="openProductAdmin()">Add Product</button>
      <p id="productMessage">Loading products...</p>
      <div id="productList"></div>
    `,

    customers: `
      <h1>Customers</h1>
      <p>Manage your customers.</p>
    `,

    reports: `
      <h1>Reports</h1>
      <p>View your sales reports.</p>
    `,

    cart: `
      <h1>Cart Activity</h1>
      <p>View customer cart activity.</p>
    `,

    favorites: `
      <h1>Favorites</h1>
      <p>View favorite products.</p>
    `,

    settings: `
      <h1>Store Settings</h1>
      <p>Edit store information.</p>
    `
  };

  content.innerHTML = pages[page] || pages.dashboard;

  if (page === "products") {
    loadProducts();
  }
}

async function loadProducts() {
  const list = document.getElementById("productList");
  const message = document.getElementById("productMessage");

  if (!list || !message) return;

  message.textContent = "Loading products...";
  list.replaceChildren();

  try {
    const response = await fetch(API_URL);

    if (!response.ok) {
      throw new Error(`Django API returned HTTP ${response.status}`);
    }

    const result = await response.json();

    if (!Array.isArray(result.products)) {
      throw new Error("The API response does not contain a products list.");
    }

    const products = result.products;

    if (products.length === 0) {
      message.textContent = "No active products found.";
      return;
    }

    message.textContent = `${products.length} product(s) found.`;

    products.forEach(product => {
      const card = document.createElement("div");

      card.style.cssText = `
        border: 1px solid #ddd;
        padding: 16px;
        margin: 12px 0;
        border-radius: 8px;
      `;

      if (product.image) {
        const image = document.createElement("img");
        image.src = product.image;
        image.alt = product.name;
        image.style.cssText =
          "width:160px;height:120px;object-fit:cover;";
        image.onerror = () => image.remove();
        card.appendChild(image);
      }

      const name = document.createElement("h3");
      name.textContent = product.name || "Unnamed product";

      const category = document.createElement("p");
      category.textContent = `Category: ${product.category || "Others"}`;

      const price = document.createElement("p");
      price.textContent = `Price: ₱${product.price}`;

      const stock = document.createElement("p");
      stock.textContent = `Stock: ${product.stock}`;

      const description = document.createElement("p");
      description.textContent = product.description || "No description available.";

      card.append(name, category, price, stock, description);
      list.appendChild(card);
    });

  } catch (error) {
    console.error("Failed to load products:", error);

    message.textContent =
      "Unable to load products. Check that Django is running and CORS is configured correctly.";
  }
}

function openProductAdmin() {
  window.open(
    "http://127.0.0.1:8000/admin/product/product/add/",
    "_blank"
  );
}
