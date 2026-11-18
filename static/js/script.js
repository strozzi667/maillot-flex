/* ==========================================
   MAILLOT FLEX - SCRIPT PRINCIPAL
   Saison 2026/2027
========================================== */

document.addEventListener("DOMContentLoaded", () => {

    // ELEMENTS
    const cartCount = document.getElementById("cartCount");
    const toast = document.getElementById("toast");

    // NOTIFICATIONS
    function showToast(message) {
        if (!toast) {
            alert(message);
            return;
        }

        toast.textContent = message;
        toast.classList.add("show");

        clearTimeout(window.mailFlexToastTimer);

        window.mailFlexToastTimer = setTimeout(() => {
            toast.classList.remove("show");
        }, 2800);
    }

    // PANIER
    function getCart() {
        try {
            return JSON.parse(localStorage.getItem("mailFlexCart")) || [];
        } catch {
            return [];
        }
    }

    function saveCart(cart) {
        localStorage.setItem("mailFlexCart", JSON.stringify(cart));
        updateCartCount();
    }

    function updateCartCount() {
        if (!cartCount) return;

        const total = getCart().reduce(
            (sum, item) => sum + Number(item.quantity || 0),
            0
        );

        cartCount.textContent = total;
    }

    // AJOUTER UNE VAREUSE AU PANIER
    function addToCart(button) {

        const productId = button.dataset.id;
        const productName = button.dataset.name;
        const productPrice = Number(button.dataset.price || 12);
        const productImage = button.dataset.image || "";
        const productSize = button.dataset.size || "M";

        if (!productId || !productName) {
            showToast("Informations du maillot manquantes.");
            return;
        }

        const cart = getCart();

        const existingProduct = cart.find(item =>
            item.id === productId && item.size === productSize
        );

        if (existingProduct) {
            existingProduct.quantity += 1;
        } else {
            cart.push({
                id: productId,
                name: productName,
                price: productPrice,
                image: productImage,
                size: productSize,
                quantity: 1
            });
        }

        saveCart(cart);
        showToast("Vareuse ajoutée au panier !");
    }

    document.querySelectorAll(".add-to-cart").forEach(button => {
        button.addEventListener("click", () => addToCart(button));
    });

    // FILTRES DES VAREUSES
    const filterButtons = document.querySelectorAll("[data-filter]");
    const productCards = document.querySelectorAll("[data-category]");

    filterButtons.forEach(button => {
        button.addEventListener("click", () => {

            const selectedFilter = button.dataset.filter;

            filterButtons.forEach(btn => btn.classList.remove("active"));
            button.classList.add("active");

            productCards.forEach(card => {
                const category = card.dataset.category;

                card.style.display =
                    selectedFilter === "all" || category === selectedFilter
                        ? ""
                        : "none";
            });
        });
    });

    // RECHERCHE DES VAREUSES
    const searchInput = document.querySelector("#searchPanel input");

    if (searchInput) {
        searchInput.addEventListener("input", () => {

            const query = searchInput.value.toLowerCase().trim();

            document.querySelectorAll("[data-product-name]").forEach(card => {

                const name = (
                    card.dataset.productName || ""
                ).toLowerCase();

                card.style.display = name.includes(query) ? "" : "none";
            });
        });
    }

    // PUBLICATION DES NOUVELLES VAREUSES
    // Les produits seront affichés ici après leur ajout
    // depuis l'espace administrateur relié à Flask et MySQL.

    const productGrid = document.getElementById("productGrid");

    function displayNewProduct(product) {

        if (!productGrid) return;

        const card = document.createElement("article");
        card.className = "maillot-card";
        card.dataset.category = product.category || "clubs";
        card.dataset.productName = product.name;

        const image = document.createElement("img");
        image.src = product.image;
        image.alt = product.name;

        const imageContainer = document.createElement("div");
        imageContainer.className = "maillot-image";
        imageContainer.appendChild(image);

        const info = document.createElement("div");
        info.className = "maillot-info";

        const club = document.createElement("span");
        club.textContent = product.club;

        const title = document.createElement("h3");
        title.textContent = product.name;

        const description = document.createElement("p");
        description.textContent = product.description || "Vareuse édition joueur";

        const bottom = document.createElement("div");
        bottom.className = "maillot-bottom";

        const price = document.createElement("strong");
        price.textContent = Number(product.price).toFixed(2) + " $";

        const addButton = document.createElement("button");
        addButton.className = "add-to-cart";
        addButton.textContent = "Ajouter au panier";
        addButton.dataset.id = product.id;
        addButton.dataset.name = product.name;
        addButton.dataset.price = product.price;
        addButton.dataset.image = product.image;

        addButton.addEventListener("click", () => addToCart(addButton));

        bottom.append(price, addButton);
        info.append(club, title, description, bottom);
        card.append(imageContainer, info);

        productGrid.prepend(card);
    }

    // ANNEE
    const yearElement = document.getElementById("currentYear");

    if (yearElement) {
        yearElement.textContent = new Date().getFullYear();
    }

    // INITIALISATION
    updateCartCount();

});