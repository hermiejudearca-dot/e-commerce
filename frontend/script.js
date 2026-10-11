
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
      <button onclick="alert('Order details opened!')">
        View Order
      </button>
    `,
    products: `
      <h1>Products</h1>
      <button onclick="addProduct()">Add Product</button>
      <ul id="productList"></ul>
    `,
    customers: "<h1>Customers</h1><p>Manage your customers.</p>",
    reports: "<h1>Reports</h1><p>View your sales reports.</p>",
    cart: "<h1>Cart Activity</h1><p>View customer cart activity.</p>",
    favorites: "<h1>Favorites</h1><p>View favorite products.</p>",
    settings: "<h1>Store Settings</h1><p>Edit store information.</p>"
  };

  content.innerHTML = pages[page] || pages.dashboard;
}

function addProduct() {
  const name = prompt("Enter product name:");

  if (!name || !name.trim()) return;

  const list = document.getElementById("productList");
  const item = document.createElement("li");

  item.textContent = name.trim();
  list.appendChild(item);
}
