
const API_ORIGIN = "http://127.0.0.1:8000";
const API_BASE = `${API_ORIGIN}/api`;
const API_URL = `${API_BASE}/products/`;

const API = {
  dashboard: `${API_BASE}/dashboard/`,
  products: API_URL,
  orders: `${API_BASE}/orders/`,
  customers: `${API_BASE}/customers/`,
  reports: `${API_BASE}/reports/`,
  cart: `${API_BASE}/cart-activity/`,
  favorites: `${API_BASE}/favorites/`,
  settings: `${API_BASE}/settings/`
};

const peso = value =>
  new Intl.NumberFormat("en-PH", {
    style: "currency",
    currency: "PHP"
  }).format(Number(value) || 0);

const escapeHTML = value =>
  String(value ?? "").replace(/[&<>"']/g, char => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  })[char]);

function getContent() {
  return document.getElementById("content") ||
         document.getElementById("main");
}

function setContent(html) {
  const container = getContent();

  if (!container) {
    console.error('Cannot find an element with id="content" or id="main".');
    return;
  }

  container.innerHTML = html;
}

async function apiRequest(url, options = {}) {
  const response = await fetch(url, options);
  let data = {};

  try {
    data = await response.json();
  } catch {}

  if (!response.ok) {
    throw new Error(
      data.error || data.detail || data.message ||
      `Request failed: HTTP ${response.status}`
    );
  }

  return data;
}

function getArray(data, key) {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.[key])) return data[key];

  for (const name of ["results", "items", "data"]) {
    if (Array.isArray(data?.[name])) return data[name];
  }

  return [];
}

function pageHeader(title, subtitle = "") {
  return `
    <h1>${escapeHTML(title)}</h1>
    ${subtitle ? `<p>${escapeHTML(subtitle)}</p>` : ""}
  `;
}

function showError(error, retryFunction) {
  return `
    <div role="alert" style="padding:12px;border:1px solid #d99;border-radius:8px;margin:12px 0;">
      <strong>Unable to load data.</strong>
      <p>${escapeHTML(error.message || "Please check your Django server and API endpoint.")}</p>
      <button type="button" onclick="${retryFunction}()">Retry</button>
    </div>
  `;
}

function formatDate(value) {
  if (!value) return "—";

  const date = new Date(value);

  return Number.isNaN(date.getTime())
    ? escapeHTML(value)
    : escapeHTML(date.toLocaleString("en-PH"));
}

function statusBadge(status) {
  return `<span style="padding:4px 8px;border-radius:8px;background:#eee;">${escapeHTML(status || "Unknown")}</span>`;
}

// NAVIGATION
async function showPage(page) {
  const pages = {
    dashboard: renderDashboard,
    products: renderProducts,
    orders: renderOrders,
    customers: renderCustomers,
    reports: renderReports,
    cart: renderCartActivity,
    favorites: renderFavorites,
    settings: renderSettings
  };

  const render = pages[page] || renderDashboard;

  try {
    await render();
  } catch (error) {
    console.error("Page loading error:", error);
    setContent(
      pageHeader("Something went wrong") +
      showError(error, `() => showPage('${page}')`)
    );
  }
}

async function renderDashboard() {
  setContent(
    pageHeader("Welcome back, Admin!", "Loading your store overview...") +
    "<p>Loading dashboard statistics...</p>"
  );

  try {
    const response = await apiRequest(API.dashboard);
    const data = response.dashboard || response;

    const totalOrders =
      data.total_orders ?? data.orders_count ?? 0;
    const totalSales =
      data.total_sales ?? data.sales_total ?? 0;
    const totalProducts =
      data.total_products ?? data.products_count ?? 0;
    const totalCustomers =
      data.total_customers ?? data.customers_count ?? 0;

    setContent(`
      ${pageHeader("Welcome back, Admin!", "Manage your store today.")}

      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:16px;">
        <section style="padding:16px;border:1px solid #ddd;border-radius:10px;">
          <p>Total Orders</p><h2>${escapeHTML(totalOrders)}</h2>
        </section>
        <section style="padding:16px;border:1px solid #ddd;border-radius:10px;">
          <p>Total Sales</p><h2>${escapeHTML(peso(totalSales))}</h2>
        </section>
        <section style="padding:16px;border:1px solid #ddd;border-radius:10px;">
          <p>Total Products</p><h2>${escapeHTML(totalProducts)}</h2>
        </section>
        <section style="padding:16px;border:1px solid #ddd;border-radius:10px;">
          <p>Total Customers</p><h2>${escapeHTML(totalCustomers)}</h2>
        </section>
      </div>

      <h2 style="margin-top:24px;">Recent Orders</h2>
      <div id="recentOrders">Loading orders...</div>
    `);

    await loadRecentOrders();
  } catch (error) {
    console.error("Dashboard error:", error);
    setContent(
      pageHeader("Dashboard") +
      showError(error, "renderDashboard")
    );
  }
}

async function loadRecentOrders() {
  const target = document.getElementById("recentOrders");
  if (!target) return;

  try {
    const data = await apiRequest(API.orders);
    const orders = getArray(data, "orders").slice(0, 5);

    if (!orders.length) {
      target.textContent = "No orders found.";
      return;
    }

    target.innerHTML = `
      <div style="overflow-x:auto;">
        <table style="width:100%;border-collapse:collapse;">
          <thead>
            <tr><th align="left">Order</th><th align="left">Customer</th><th align="left">Total</th><th align="left">Status</th></tr>
          </thead>
          <tbody>
            ${orders.map(order => `
              <tr>
                <td>${escapeHTML(order.order_number || order.id || "—")}</td>
                <td>${escapeHTML(order.customer_name || order.customer || "Guest")}</td>
                <td>${escapeHTML(peso(order.total_amount ?? order.total ?? 0))}</td>
                <td>${statusBadge(order.status)}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    `;
  } catch (error) {
    console.error("Recent orders error:", error);
    target.innerHTML = showError(error, "loadRecentOrders");
  }
}

async function renderProducts() {
  setContent(`
    ${pageHeader("Products", "Products loaded from Django.")}
    <button type="button" onclick="openProductAdmin()">Add Product</button>
    <p id="productMessage">Loading products...</p>
    <div id="productList"></div>
  `);

  await loadProducts();
}

async function loadProducts() {
  const list = document.getElementById("productList");
  const message = document.getElementById("productMessage");

  if (!list || !message) return;

  message.textContent = "Loading products...";
  list.replaceChildren();

  try {
    const data = await apiRequest(API.products);

    if (!Array.isArray(data.products)) {
      throw new Error("The API response does not contain a products list.");
    }

    const products = data.products;

    if (products.length === 0) {
      message.textContent = "No active products found.";
      return;
    }

    message.textContent = `${products.length} product(s) found.`;

    products.forEach(product => {
      const card = document.createElement("article");

      card.style.cssText =
        "border:1px solid #ddd;padding:16px;margin:12px 0;border-radius:8px;";

      if (product.image) {
        const image = document.createElement("img");
        image.src = product.image;
        image.alt = product.name || "Product image";
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
      price.textContent = `Price: ${peso(product.price)}`;

      const stock = document.createElement("p");
      stock.textContent = `Stock: ${product.stock ?? 0}`;

      const description = document.createElement("p");
      description.textContent =
        product.description || "No description available.";

      card.append(name, category, price, stock, description);
      list.appendChild(card);
    });
  } catch (error) {
    console.error("Products error:", error);
    message.textContent = "Unable to load products.";
    list.innerHTML = showError(error, "loadProducts");
  }
}

function openProductAdmin() {
  window.open(
    `${API_ORIGIN}/admin/product/product/add/`,
    "_blank",
    "noopener"
  );
}

async function renderOrders() {
  setContent(
    pageHeader("Orders", "Manage customer orders.") +
    '<p id="ordersMessage">Loading orders...</p><div id="ordersList"></div>'
  );

  const message = document.getElementById("ordersMessage");
  const list = document.getElementById("ordersList");

  try {
    const data = await apiRequest(API.orders);
    const orders = getArray(data, "orders");

    if (!orders.length) {
      message.textContent = "No orders found.";
      return;
    }

    message.textContent = `${orders.length} order(s) found.`;

    list.innerHTML = `
      <div style="overflow-x:auto;">
        <table style="width:100%;border-collapse:collapse;">
          <thead><tr>
            <th align="left">Order ID</th><th align="left">Customer</th>
            <th align="left">Items</th><th align="left">Total</th>
            <th align="left">Status</th><th align="left">Date</th>
          </tr></thead>
          <tbody>
            ${orders.map(order => {
              const itemCount = order.items_count ??
                (Array.isArray(order.items)
                  ? order.items.reduce((sum, item) => sum + Number(item.quantity || 0), 0)
                  : "—");

              return `<tr>
                <td>${escapeHTML(order.order_number || order.id || "—")}</td>
                <td>${escapeHTML(order.customer_name || order.customer || "Guest")}</td>
                <td>${escapeHTML(itemCount)}</td>
                <td>${escapeHTML(peso(order.total_amount ?? order.total ?? 0))}</td>
                <td>${statusBadge(order.status)}</td>
                <td>${formatDate(order.date_ordered || order.date || order.created_at)}</td>
              </tr>`;
            }).join("")}
          </tbody>
        </table>
      </div>
    `;
  } catch (error) {
    console.error("Orders error:", error);
    message.textContent = "";
    list.innerHTML = showError(error, "renderOrders");
  }
}

async function renderCustomers() {
  setContent(
    pageHeader("Customers", "Customer records from Django.") +
    '<p id="customersMessage">Loading customers...</p><div id="customersList"></div>'
  );

  const message = document.getElementById("customersMessage");
  const list = document.getElementById("customersList");

  try {
    const data = await apiRequest(API.customers);
    const customers = getArray(data, "customers");

    if (!customers.length) {
      message.textContent = "No customers found.";
      return;
    }

    message.textContent = `${customers.length} customer(s) found.`;

    list.innerHTML = `
      <div style="overflow-x:auto;">
        <table style="width:100%;border-collapse:collapse;">
          <thead><tr>
            <th align="left">ID</th><th align="left">Name</th>
            <th align="left">Email</th><th align="left">Joined</th>
          </tr></thead>
          <tbody>
            ${customers.map(customer => `
              <tr>
                <td>${escapeHTML(customer.id ?? "—")}</td>
                <td>${escapeHTML(customer.name || "—")}</td>
                <td>${escapeHTML(customer.email || "—")}</td>
                <td>${formatDate(customer.created_at || customer.date_joined)}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    `;
  } catch (error) {
    console.error("Customers error:", error);
    message.textContent = "";
    list.innerHTML = showError(error, "renderCustomers");
  }
}

async function renderReports() {
  setContent(
    pageHeader("Reports", "Sales and order summaries.") +
    '<p id="reportsMessage">Loading reports...</p><div id="reportsContent"></div>'
  );

  const message = document.getElementById("reportsMessage");
  const target = document.getElementById("reportsContent");

  try {
    const response = await apiRequest(API.reports);
    const report = response.report || response;

    message.textContent = "Reports loaded.";

    target.innerHTML = `
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:16px;">
        <section style="padding:16px;border:1px solid #ddd;border-radius:10px;">
          <p>Total Sales</p><h2>${escapeHTML(peso(report.total_sales ?? report.sales_total ?? 0))}</h2>
        </section>
        <section style="padding:16px;border:1px solid #ddd;border-radius:10px;">
          <p>Total Orders</p><h2>${escapeHTML(report.total_orders ?? report.orders_count ?? 0)}</h2>
        </section>
        <section style="padding:16px;border:1px solid #ddd;border-radius:10px;">
          <p>Paid Orders</p><h2>${escapeHTML(report.paid_orders ?? 0)}</h2>
        </section>
        <section style="padding:16px;border:1px solid #ddd;border-radius:10px;">
          <p>Pending Orders</p><h2>${escapeHTML(report.pending_orders ?? 0)}</h2>
        </section>
      </div>
    `;

    if (Array.isArray(report.sales_by_month) && report.sales_by_month.length) {
      target.innerHTML += `
        <h2>Sales by Month</h2>
        <table style="width:100%;border-collapse:collapse;">
          <thead><tr><th align="left">Month</th><th align="left">Sales</th></tr></thead>
          <tbody>
            ${report.sales_by_month.map(row => `
              <tr>
                <td>${escapeHTML(row.month || row.label || "—")}</td>
                <td>${escapeHTML(peso(row.total_sales ?? row.total ?? 0))}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      `;
    }
  } catch (error) {
    console.error("Reports error:", error);
    message.textContent = "";
    target.innerHTML = showError(error, "renderReports");
  }
}

async function renderCartActivity() {
  setContent(
    pageHeader("Cart Activity", "Customer cart activity.") +
    '<p id="cartMessage">Loading cart activity...</p><div id="cartList"></div>'
  );

  const message = document.getElementById("cartMessage");
  const list = document.getElementById("cartList");

  try {
    const data = await apiRequest(API.cart);
    const rows = getArray(data, "cart_activity");

    if (!rows.length) {
      message.textContent = "No cart activity records found.";
      return;
    }

    message.textContent = `${rows.length} record(s) found.`;

    list.innerHTML = `
      <table style="width:100%;border-collapse:collapse;">
        <thead><tr><th align="left">Customer</th><th align="left">Product</th><th align="left">Quantity</th><th align="left">Activity</th><th align="left">Date</th></tr></thead>
        <tbody>
          ${rows.map(row => `
            <tr>
              <td>${escapeHTML(row.customer_name || row.customer || "Guest")}</td>
              <td>${escapeHTML(row.product_name || row.product || "—")}</td>
              <td>${escapeHTML(row.quantity ?? 1)}</td>
              <td>${escapeHTML(row.action || row.activity || "Added to cart")}</td>
              <td>${formatDate(row.created_at || row.date)}</td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    `;
  } catch (error) {
    console.error("Cart activity error:", error);
    message.textContent = "";
    list.innerHTML = showError(error, "renderCartActivity");
  }
}

async function renderFavorites() {
  setContent(
    pageHeader("Favorites", "Products customers have favorited.") +
    '<p id="favoritesMessage">Loading favorites...</p><div id="favoritesList"></div>'
  );

  const message = document.getElementById("favoritesMessage");
  const list = document.getElementById("favoritesList");

  try {
    const data = await apiRequest(API.favorites);
    const favorites = getArray(data, "favorites");

    if (!favorites.length) {
      message.textContent = "No favorites found.";
      return;
    }

    message.textContent = `${favorites.length} favorite(s) found.`;

    list.innerHTML = `
      <table style="width:100%;border-collapse:collapse;">
        <thead><tr><th align="left">Customer</th><th align="left">Product</th><th align="left">Price</th><th align="left">Date</th></tr></thead>
        <tbody>
          ${favorites.map(item => `
            <tr>
              <td>${escapeHTML(item.customer_name || item.customer || "—")}</td>
              <td>${escapeHTML(item.product_name || item.product || "—")}</td>
              <td>${escapeHTML(peso(item.price ?? item.product_price ?? 0))}</td>
              <td>${formatDate(item.created_at || item.date)}</td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    `;
  } catch (error) {
    console.error("Favorites error:", error);
    message.textContent = "";
    list.innerHTML = showError(error, "renderFavorites");
  }
}

async function renderSettings() {
  setContent(
    pageHeader("Store Settings", "Store information from Django.") +
    '<p id="settingsMessage">Loading settings...</p><div id="settingsContent"></div>'
  );

  const message = document.getElementById("settingsMessage");
  const target = document.getElementById("settingsContent");

  try {
    const response = await apiRequest(API.settings);
    const settings = response.settings || response;

    message.textContent = "Settings loaded.";

    target.innerHTML = `
      <form id="storeSettingsForm" style="display:grid;gap:12px;max-width:520px;">
        <label>Store Name
          <input name="store_name" required value="${escapeHTML(settings.store_name || "")}" style="display:block;width:100%;padding:10px;">
        </label>
        <label>Email
          <input name="email" type="email" value="${escapeHTML(settings.email || "")}" style="display:block;width:100%;padding:10px;">
        </label>
        <label>Phone
          <input name="phone" value="${escapeHTML(settings.phone || "")}" style="display:block;width:100%;padding:10px;">
        </label>
        <label>Address
          <textarea name="address" rows="3" style="display:block;width:100%;padding:10px;">${escapeHTML(settings.address || "")}</textarea>
        </label>
        <button type="submit">Save Settings</button>
        <p id="settingsSaveMessage" role="status"></p>
      </form>
    `;

    document.getElementById("storeSettingsForm").addEventListener("submit", async event => {
      event.preventDefault();

      const status = document.getElementById("settingsSaveMessage");
      const payload = Object.fromEntries(new FormData(event.currentTarget).entries());

      status.textContent = "Saving...";

      try {
        await apiRequest(API.settings, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });

        status.textContent = "Settings saved successfully.";
      } catch (error) {
        console.error("Save settings error:", error);
        status.textContent = `Could not save settings: ${error.message}`;
      }
    });
  } catch (error) {
    console.error("Settings error:", error);
    message.textContent = "";
    target.innerHTML = showError(error, "renderSettings");
  }
}

function refreshCurrentPage(page = "dashboard") {
  return showPage(page);
}

document.addEventListener("DOMContentLoaded", () => {
  if (getContent()) {
    showPage("dashboard");
  }
});
