/* ============================================================ ALWAYSSMILE — MERCHANDISE PLANOGRAM ============================================================ */

(() => { "use strict";

const urls = window.MERCHANDISE_URLS;

if (!urls) {
    console.error("MERCHANDISE_URLS configuration is missing.");
    return;
}

const elements = {
    floorSelector: document.getElementById("floorSelector"),
    floorCanvas: document.getElementById("floorCanvas"),
    exportFloor: document.getElementById("exportFloor"),
    clearFloor: document.getElementById("clearFloor"),

    fixtureForm: document.getElementById("fixtureForm"),
    fixtureName: document.getElementById("fixtureName"),
    fixtureType: document.getElementById("fixtureType"),
    fixtureX: document.getElementById("fixtureX"),
    fixtureY: document.getElementById("fixtureY"),
    fixtureWidth: document.getElementById("fixtureWidth"),
    fixtureDepth: document.getElementById("fixtureDepth"),
    fixtureMessage: document.getElementById("fixtureMessage"),

    fixtureDetails: document.getElementById("fixtureDetails"),
    planogramContainer: document.getElementById("planogramContainer"),

    productSearch: document.getElementById("productSearch"),
    productResults: document.getElementById("productResults")
};

let currentFloor = null;
let currentFloorData = null;
let currentFixtures = [];
let currentRooms = [];
let selectedFixture = null;
let products = [];
let floorRequestSequence = 0;

const csrfToken = getCookie("csrftoken");

/* ========================================================
   HELPERS
   ======================================================== */

function getCookie(name) {
    const cookies = document.cookie.split(";");

    for (const cookie of cookies) {
        const value = cookie.trim();

        if (value.startsWith(name + "=")) {
            return decodeURIComponent(value.substring(name.length + 1));
        }
    }

    return "";
}

function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, character => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;"
    })[character]);
}

function endpoint(template, id) {
    return template.replace("999999", encodeURIComponent(id));
}

async function apiRequest(url, options = {}) {
    const response = await fetch(url, {
        ...options,
        headers: {
            "X-CSRFToken": csrfToken,
            ...(options.headers || {})
        }
    });

    let data;

    try {
        data = await response.json();
    } catch {
        throw new Error("The server returned an invalid response.");
    }

    if (!response.ok || data.success === false) {
        throw new Error(data.error || "Request failed.");
    }

    return data;
}

function showMessage(message, success = true) {
    if (!elements.fixtureMessage) return;

    elements.fixtureMessage.textContent = message;

    elements.fixtureMessage.className =
        "mt-3 text-sm " +
        (success ? "text-green-700" : "text-red-700");
}

function setLoading(element, message) {
    element.innerHTML = `
        <p class="p-4 text-sm text-gray-500">
            ${escapeHTML(message)}
        </p>
    `;
}

/* ========================================================
   FLOOR LOADING
   ======================================================== */

async function loadFloor() {
    const floorId = elements.floorSelector?.value;

    if (!floorId) {
        setLoading(elements.floorCanvas, "No floor selected.");
        return;
    }

    if (String(currentFloor) !== String(floorId)) {
        selectedFixture = null;
    }

    currentFloor = floorId;
    currentFloorData = null;

    setLoading(elements.floorCanvas, "Loading floor plan...");
    setLoading(elements.fixtureDetails, "Select a fixture.");
    setLoading(elements.planogramContainer, "Select a fixture.");

    try {
        const data = await apiRequest(
            endpoint(urls.floor, floorId)
        );

        if (!data.floor) {
            throw new Error("Floor information is missing.");
        }

        if (!Number(data.floor.width) || !Number(data.floor.height)) {
            throw new Error("Invalid floor dimensions.");
        }

        // Keep the entire response, including architectural features.
        currentFloorData = data;
        currentRooms = Array.isArray(data.rooms) ? data.rooms : [];
        currentFixtures = Array.isArray(data.fixtures)
            ? data.fixtures
            : [];

        renderFloor(
            data.floor,
            data.architectural?.features || []
        );

    } catch (error) {
        setLoading(elements.floorCanvas, error.message);
        console.error("Floor loading error:", error);
    }
}

function renderArchitecturalFeatures(features, floor) {
    const width = Number(floor.width);
    const height = Number(floor.height);

    if (!width || !height || !Array.isArray(features)) return "";

    return features.map(feature => {
        const left = (Number(feature.x) / width) * 100;
        const top = (Number(feature.y) / height) * 100;
        const featureWidth = (Number(feature.width) / width) * 100;
        const featureHeight = (Number(feature.height) / height) * 100;

        if (![left, top, featureWidth, featureHeight].every(Number.isFinite)) {
            return "";
        }

        return `
            <div class="floor-architecture floor-architecture--${escapeHTML(feature.kind)}"
                 aria-hidden="true"
                 style="left:${left}%;top:${top}%;width:${featureWidth}%;height:${featureHeight}%">
            </div>
        `;
    }).join("");
}

/* ========================================================
   FLOOR RENDERING
   ======================================================== */

function renderFloor(floor, architecturalFeatures = []) {
    const canvas = elements.floorCanvas;

    const width = Number(floor.width);
    const height = Number(floor.height);

    if (!width || !height) {
        setLoading(canvas, "Invalid floor dimensions.");
        return;
    }

    canvas.style.position = "relative";
    canvas.style.width = "100%";
    canvas.style.aspectRatio = `${width} / ${height}`;
    canvas.style.overflow = "hidden";

    canvas.dataset.width = width;
    canvas.dataset.height = height;

    canvas.innerHTML = "";

    canvas.insertAdjacentHTML(
        "beforeend",
        renderArchitecturalFeatures(architecturalFeatures, floor)
    );

    currentRooms.forEach(room => {
        const element = document.createElement("div");

        element.className = "floor-room";

        element.style.left = `${Number(room.x) / width * 100}%`;
        element.style.top = `${Number(room.y) / height * 100}%`;
        element.style.width = `${Number(room.width) / width * 100}%`;
        element.style.height = `${Number(room.height) / height * 100}%`;
        element.style.background = room.color || "#DBEAFE";
        element.textContent = room.name;

        canvas.appendChild(element);
    });

    currentFixtures.forEach(fixture => {
        renderFixture(fixture, width, height);
    });
}


function renderFixture(fixture, floorWidth, floorHeight) {
    const element = document.createElement("button");

    element.type = "button";

    element.className = "floor-fixture";
    if (String(selectedFixture?.id) === String(fixture.id)) {
        element.classList.add("selected");
    }
        // "absolute flex items-center justify-center " +
        // "overflow-hidden rounded border-2 border-blue-800 " +
        // "bg-blue-600 p-1 text-center text-xs font-semibold text-white " +
        // "hover:bg-blue-700";

    element.style.left =
        `${Number(fixture.x) / floorWidth * 100}%`;

    element.style.top =
        `${Number(fixture.y) / floorHeight * 100}%`;

    element.style.width =
        `${Number(fixture.width) / floorWidth * 100}%`;

    element.style.height =
        `${Number(fixture.depth) / floorHeight * 100}%`;

    element.textContent = fixture.name;

    element.addEventListener("click", () => {
        selectFixture(fixture);
    });

    if (String(selectedFixture?.id) === String(fixture.id)) {
        element.style.outline = "3px solid #F59E0B";
    }

    elements.floorCanvas.appendChild(element);
}

/* ========================================================
   FIXTURE SELECTION
   ======================================================== */

async function selectFixture(fixture) {
    selectedFixture = fixture;

    if (currentFloorData) {
        renderFloor(
            currentFloorData.floor,
            currentFloorData.architectural?.features || []
        );
    }

    // fixture details and planogram loading code.

    elements.fixtureDetails.innerHTML = `
        <div class="space-y-3">
            <h3 class="font-semibold text-gray-900">
                ${escapeHTML(fixture.name)}
            </h3>

            <p>Type: ${escapeHTML(fixture.type || fixture.fixture_type)}</p>
            <p>X: ${escapeHTML(fixture.x)} m</p>
            <p>Y: ${escapeHTML(fixture.y)} m</p>
            <p>Width: ${escapeHTML(fixture.width)} m</p>
            <p>Depth: ${escapeHTML(fixture.depth)} m</p>

            <button
                type="button"
                id="deleteSelectedFixture"
                class="rounded-lg bg-red-600 px-4 py-2 text-white hover:bg-red-700">
                Delete Fixture
            </button>
        </div>
    `;

    document.getElementById("deleteSelectedFixture")
        .addEventListener("click", deleteSelectedFixture);

    await loadPlanogram(fixture.id);
}

/* ========================================================
   ADD FIXTURE
   ======================================================== */

async function addFixture(event) {
    event.preventDefault();

    const floorId = currentFloor;

    if (!floorId) {
        showMessage("Please select a floor.", false);
        return;
    }

    const payload = {
        name: elements.fixtureName.value.trim(),
        fixture_type: elements.fixtureType.value,
        x: Number(elements.fixtureX.value),
        y: Number(elements.fixtureY.value),
        width: Number(elements.fixtureWidth.value),
        depth: Number(elements.fixtureDepth.value)
    };

    if (
        !payload.name ||
        !Number.isFinite(payload.x) ||
        !Number.isFinite(payload.y) ||
        !Number.isFinite(payload.width) ||
        !Number.isFinite(payload.depth) ||
        payload.x < 0 ||
        payload.y < 0 ||
        payload.width <= 0 ||
        payload.depth <= 0
    ) {
        showMessage("Please enter valid fixture information.", false);
        return;
    }

    try {
        const data = await apiRequest(
            endpoint(urls.addFixture, floorId),
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(payload)
            }
        );

        showMessage("Fixture added successfully.");

        elements.fixtureForm.reset();

        if (data.fixture) {
            selectedFixture = data.fixture;
        }

        await loadFloor();

    } catch (error) {
        showMessage(error.message, false);
    }
}

/* ========================================================
   DELETE FIXTURE
   ======================================================== */

async function deleteSelectedFixture() {
    if (!selectedFixture) return;

    if (!confirm("Delete this fixture and its planogram?")) {
        return;
    }

    try {
        await apiRequest(
            endpoint(urls.deleteFixture, selectedFixture.id),
            {
                method: "POST"
            }
        );

        selectedFixture = null;

        await loadFloor();

        showMessage("Fixture deleted successfully.");

    } catch (error) {
        showMessage(error.message, false);
    }
}

/* ========================================================
   PRODUCT CATALOGUE
   ======================================================== */

async function loadProducts(search = "") {
    setLoading(elements.productResults, "Loading products...");

    try {
        const url = new URL(
            urls.products,
            window.location.origin
        );

        url.searchParams.set("search", search);

        const data = await apiRequest(url.toString());

        products = data.products || [];

        renderProducts(products);

    } catch (error) {
        setLoading(elements.productResults, error.message);
        console.error("Product loading error:", error);
    }
}

function renderProducts(items) {
    if (!items.length) {
        setLoading(elements.productResults, "No products found.");
        return;
    }

    elements.productResults.innerHTML = items.map(product => `
        <article class="rounded-xl border border-gray-200 bg-white p-4">

            <img
                src="${escapeHTML(product.thumbnail || "")}"
                alt="${escapeHTML(product.title)}"
                class="mb-3 h-36 w-full rounded-lg object-contain"
                loading="lazy"
            >

            <h3 class="font-semibold text-gray-900">
                ${escapeHTML(product.title)}
            </h3>

            <p class="mt-1 text-sm text-gray-500">
                ${escapeHTML(product.category)}
            </p>

            <p class="mt-2 font-semibold text-blue-700">
                $${escapeHTML(product.price)}
            </p>

            <p class="text-xs text-gray-500">
                Stock: ${escapeHTML(product.stock)}
            </p>

            <button
                type="button"
                data-product-id="${escapeHTML(product.id)}"
                class="mt-3 w-full rounded-lg bg-blue-600 px-3 py-2 text-sm font-semibold text-white hover:bg-blue-700">
                Add to Selected Fixture
            </button>

        </article>
    `).join("");

    elements.productResults
        .querySelectorAll("[data-product-id]")
        .forEach(button => {
            button.addEventListener("click", () => {
                addProductToFixture(button.dataset.productId);
            });
        });
}

/* ========================================================
   ADD PRODUCT TO PLANOGRAM
   ======================================================== */

async function addProductToFixture(productId) {
    if (!selectedFixture) {
        alert("Please select a fixture first.");
        return;
    }

    const quantity = Number(
        prompt("Enter product quantity:", "1")
    );

    if (!Number.isInteger(quantity) || quantity < 1 || quantity > 10000) {
        alert("Enter a valid quantity between 1 and 10000.");
        return;
    }

    const facings = Number(
        prompt("Enter number of facings:", "1")
    );

    if (
        !Number.isInteger(facings) ||
        facings < 1 ||
        facings > quantity
    ) {
        alert("Facings must be between 1 and the product quantity.");
        return;
    }

    try {
        await apiRequest(
            endpoint(urls.addItem, selectedFixture.id),
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    product_id: productId,
                    quantity: quantity,
                    facings: facings
                })
            }
        );

        await loadPlanogram(selectedFixture.id);

        alert("Product added successfully.");

    } catch (error) {
        alert(error.message);
    }
}

/* ========================================================
   LOAD PLANOGRAM
   ======================================================== */

async function loadPlanogram(fixtureId) {
    try {
        const data = await apiRequest(
            endpoint(urls.fixturePlanogram, fixtureId)
        );

        renderPlanogram(data);

    } catch (error) {
        setLoading(
            elements.planogramContainer,
            "Unable to load planogram. Check the fixture planogram endpoint."
        );

        console.error(error);
    }
}

/* ========================================================
   RENDER PLANOGRAM
   ======================================================== */

function renderPlanogram(data) {
    const items = data.items ||
        data.planogram_items ||
        data.planogram?.items ||
        [];

    if (!items.length) {
        setLoading(
            elements.planogramContainer,
            "No products assigned to this fixture."
        );
        return;
    }

    elements.planogramContainer.innerHTML = `
        <div class="overflow-x-auto">
            <table class="w-full text-left text-sm">
                <thead class="border-b bg-gray-50">
                    <tr>
                        <th class="p-3">Product</th>
                        <th class="p-3">Quantity</th>
                        <th class="p-3">Facings</th>
                        <th class="p-3">Action</th>
                    </tr>
                </thead>

                <tbody>
                    ${items.map(item => `
                        <tr class="border-b">
                            <td class="p-3">
                                ${escapeHTML(item.title || item.product_title || item.product?.title)}
                            </td>

                            <td class="p-3">
                                ${escapeHTML(item.quantity)}
                            </td>

                            <td class="p-3">
                                ${escapeHTML(item.facings)}
                            </td>

                            <td class="p-3">
                                <button
                                    type="button"
                                    data-item-id="${escapeHTML(item.id)}"
                                    class="rounded bg-red-50 px-3 py-1 text-red-700 hover:bg-red-100">
                                    Remove
                                </button>
                            </td>
                        </tr>
                    `).join("")}
                </tbody>
            </table>
        </div>
    `;

    elements.planogramContainer
        .querySelectorAll("[data-item-id]")
        .forEach(button => {
            button.addEventListener("click", () => {
                deletePlanogramItem(button.dataset.itemId);
            });
        });
}

/* ========================================================
   DELETE PLANOGRAM ITEM
   ======================================================== */

async function deletePlanogramItem(itemId) {
    if (!confirm("Remove this product from the planogram?")) {
        return;
    }

    try {
        await apiRequest(
            endpoint(urls.deleteItem, itemId),
            {
                method: "POST"
            }
        );

        if (selectedFixture) {
            await loadPlanogram(selectedFixture.id);
        }

    } catch (error) {
        alert(error.message);
    }
}

/* ========================================================
   CLEAR FLOOR FIXTURES
   ======================================================== */

async function clearFloor() {
    if (!currentFloor) return;

    if (!confirm("Remove all fixtures from this floor?")) {
        return;
    }

    try {
        await apiRequest(
            endpoint(urls.clearFloor, currentFloor),
            {
                method: "POST"
            }
        );

        selectedFixture = null;

        await loadFloor();

        showMessage("Floor fixtures cleared successfully.");

    } catch (error) {
        showMessage(error.message, false);
    }
}

/* ========================================================
   EXPORT FLOOR
   ======================================================== */

async function exportFloor() {
    if (!currentFloor) return;

    try {
        const data = await apiRequest(
            endpoint(urls.exportFloor, currentFloor),
            {
                method: "POST"
            }
        );

        if (data.config) {
            const blob = new Blob(
                [JSON.stringify(data.config, null, 2)],
                { type: "application/json" }
            );

            const downloadUrl = URL.createObjectURL(blob);

            const link = document.createElement("a");

            link.href = downloadUrl;
            link.download = `floor-${currentFloor}-plan.json`;

            document.body.appendChild(link);
            link.click();
            link.remove();

            URL.revokeObjectURL(downloadUrl);
        }

        showMessage(data.message || "Floor drawing exported.");

    } catch (error) {
        showMessage(error.message, false);
    }
}

/* ========================================================
   EVENT LISTENERS
   ======================================================== */

elements.floorSelector?.addEventListener(
    "change",
    loadFloor
);

elements.fixtureForm?.addEventListener(
    "submit",
    addFixture
);

elements.clearFloor?.addEventListener(
    "click",
    clearFloor
);

elements.exportFloor?.addEventListener(
    "click",
    exportFloor
);

let searchTimeout;

elements.productSearch?.addEventListener("input", event => {
    clearTimeout(searchTimeout);

    searchTimeout = setTimeout(() => {
        loadProducts(event.target.value.trim());
    }, 350);
});

/* ========================================================
   INITIALIZE
   ======================================================== */

async function initialize() {
    if (!elements.floorSelector || !elements.floorCanvas) {
        console.error("Merchandise page elements are missing.");
        return;
    }

    if (elements.floorSelector.value) {
        await loadFloor();
    }

    await loadProducts();
}

initialize();


})();
