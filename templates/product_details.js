document.addEventListener("DOMContentLoaded", function () {
    // Get the product ID from the URL
    const urlParams = new URLSearchParams(window.location.search);
    const productId = urlParams.get("id");

    if (!productId) {
        alert("Invalid product!");
        window.location.href = "stationary.html";
        return;
    }

    // Fetch product data from the database (for now, use dummy data)
    const products = JSON.parse(localStorage.getItem("products")) || []; // Assuming products are stored in localStorage
    const product = products.find(item => item.id == productId);

    if (!product) {
        alert("Product not found!");
        window.location.href = "stationary.html";
        return;
    }

    // Populate the details page
    document.getElementById("product-image").src = product.image_url;
    document.getElementById("product-name").textContent = product.name;
    document.getElementById("product-category").textContent = product.category;
    document.getElementById("product-price").textContent = product.price;
    document.getElementById("product-stock").textContent = product.stock;
    document.getElementById("product-description").textContent = product.description;
});
