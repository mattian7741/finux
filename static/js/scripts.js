// Function to show transactions in the modal
function showTransactions(merchantId) {
    const encodedMerchantId = encodeURIComponent(merchantId);
    fetch(`/merchant_detail?merchant_id=${encodedMerchantId}`)
        .then(response => response.text())
        .then(html => {
            document.getElementById('popup-content').innerHTML = html;
            document.getElementById('popup-overlay').style.display = 'flex';
        })
        .catch(error => console.error('Error loading transaction details:', error));
}

// Function to close the popup
function closePopup() {
    document.getElementById('popup-overlay').style.display = 'none';
}

// Sorting functionality
let sortState = { column: null, order: 'none' };

function toggleSort(columnIndex) {
    if (sortState.column === columnIndex) {
        sortState.order = sortState.order === 'asc' ? 'desc' : (sortState.order === 'desc' ? 'none' : 'asc');
    } else {
        sortState.column = columnIndex;
        sortState.order = 'asc';
    }

    document.querySelectorAll('th').forEach(th => th.classList.remove('sorted-asc', 'sorted-desc'));
    const th = document.querySelectorAll('th')[columnIndex];
    if (sortState.order === 'asc') th.classList.add('sorted-asc');
    else if (sortState.order === 'desc') th.classList.add('sorted-desc');
    
    sortTable(columnIndex, sortState.order);
}

function sortTable(columnIndex, order) {
    const tableBody = document.getElementById('merchants-body');
    const rows = Array.from(tableBody.rows);

    if (order === 'none') {
        rows.sort((a, b) => a.rowIndex - b.rowIndex);
    } else {
        rows.sort((a, b) => {
            const cellA = a.cells[columnIndex];
            const cellB = b.cells[columnIndex];
            const valueA = cellA.querySelector('input') ? cellA.querySelector('input').value.trim() : cellA.textContent.trim();
            const valueB = cellB.querySelector('input') ? cellB.querySelector('input').value.trim() : cellB.textContent.trim();

            if (order === 'asc') return valueA.localeCompare(valueB, undefined, { numeric: true });
            else return valueB.localeCompare(valueA, undefined, { numeric: true });
        });
    }
    rows.forEach(row => tableBody.appendChild(row));
}

function updateCategory(merchantId, newCategory) {
    fetch(`/update_category`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ merchant_id: merchantId, category: newCategory })
    }).then(response => {
        if (response.ok) console.log('Category updated successfully');
        else console.error('Failed to update category');
    }).catch(error => console.error('Error:', error));
}

function copyTxCategoryToCategory(merchantId, txCategory) {
    const categoryInput = document.getElementById(`category-${merchantId}`);
    if (categoryInput.value.trim() === '') {
        categoryInput.value = txCategory;
        updateCategory(merchantId, txCategory);
    }
}

// Additional scripts for transactions.html
let chart;

document.addEventListener("DOMContentLoaded", function() {
    const today = new Date().toISOString().split('T')[0];
    const startOfYear = new Date(new Date().getFullYear(), 0, 1).toISOString().split('T')[0];
    const urlParams = new URLSearchParams(window.location.search);

    document.getElementById('startDate').value = urlParams.get('startDate') || startOfYear;
    document.getElementById('endDate').value = urlParams.get('endDate') || today;

    const bucketSize = urlParams.get('bucketSize') || 'day';
    document.querySelector(`input[name="bucketSize"][value="${bucketSize}"]`).checked = true;

    fetchAndRenderChartData();
});

function toggleStackedMode() {
    fetchAndRenderChartData();
}

function fetchAndRenderChartData() {
    const ctx = document.getElementById('amountChart').getContext('2d');
    const params = new URLSearchParams(window.location.search);
    const isStacked = document.getElementById('stackToggle').checked;

    const selectedCategories = Array.from(document.getElementById('categoryFilter').selectedOptions).map(option => option.value);
    params.delete('tx_category');
    selectedCategories.forEach(cat => params.append('tx_category', cat));

    const selectedAccounts = Array.from(document.getElementById('accountFilter').selectedOptions).map(option => option.value);
    params.delete('account');
    selectedAccounts.forEach(acc => params.append('account', acc));

    const endpoint = isStacked ? '/data' : '/data_combined';

    fetch(endpoint + '?' + params.toString())
        .then(response => response.json())
        .then(data => {
            if (!data || Object.keys(data).length === 0) {
                if (chart) chart.destroy();
                return;
            }

            const dates = isStacked ? Object.values(data)[0].map(entry => entry.date) : data.map(entry => entry.date);
            let datasets;
            let cumulativeSum = 0; // Initialize cumulative sum variable
            let lineData = []; // Array to hold line data for integral

            if (isStacked) {
                datasets = Object.keys(data).map((category, index) => ({
                    label: category,
                    data: data[category].map(entry => entry.amount),
                    backgroundColor: data[category].map(entry => getColorBasedOnValue(entry.amount)), // Set color based on value
                    borderColor: `rgba(${Math.random() * 255}, ${Math.random() * 255}, ${Math.random() * 255}, 1)`,
                    borderWidth: 0
                }));
            } else {
                datasets = [{
                    label: 'Combined Amount',
                    data: data.map(entry => entry.amount),
                    backgroundColor: data.map(entry => getColorBasedOnValue(entry.amount)), // Set color based on value
                    borderColor: 'rgba(75, 192, 192, 1)',
                    borderWidth: 0
                }];
            }

            // Calculate the cumulative sum for the line chart
            if (!isStacked) {
                data.forEach(entry => {
                    cumulativeSum += entry.amount; // Incremental sum
                    lineData.push(cumulativeSum); // Push the current sum to lineData
                });
            }

            if (chart) chart.destroy();

            // Create the chart
            chart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: dates,
                    datasets: [
                        ...datasets,
                        {
                            label: 'Cumulative Sum',
                            data: lineData.map(sum => sum),
                            type: 'line',
                            backgroundColor: 'rgba(0, 0, 0, 0.1)',
                            fill: true,
                            borderWidth: 0,
                            pointRadius: 0 // This removes the circles at each point
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: { type: 'time', stacked: isStacked, time: { unit: params.get('bucketSize') || 'day' }},
                        y: { beginAtZero: true, stacked: isStacked }
                    }
                }
            });
        })
        .catch(error => console.error('Error loading the data:', error));
}

// Function to determine color based on the value
function getColorBasedOnValue(value) {
    const maxSaturationValue = 1000; // Value above which color saturation is fully applied
    const minSaturationValue = 0; // Minimum value for saturation

    let r, g, b; // RGB color components
    let saturation;

    // Determine saturation based on the absolute value of the input
    if (value === 0) {
        saturation = 0; // 0 saturation if value is 0
    } else {
        saturation = Math.min(1.0, Math.abs(value) * 0.001); // Calculate saturation
    }

    // Set colors based on the sign of the value
    if (value > 0) {
        // Positive values - Green
        r = 0; // No red
        g = Math.floor(127 * saturation); // Green based on saturation
        b = Math.floor(63 * saturation);; // No blue
    } else {
        // Negative values - Red
        r = Math.floor(127 * saturation); // Red based on saturation
        g = 0; // No green
        b = 0; // No blue
    }

    return `rgba(${r}, ${g}, ${b}, 0.5)`; // Return the color in RGBA format
}



function applyFilter() {
    const queryParams = new URLSearchParams(window.location.search);
    queryParams.set('startDate', document.getElementById('startDate').value);
    queryParams.set('endDate', document.getElementById('endDate').value);
    queryParams.delete('tx_category');
    queryParams.delete('account');  // New: Clear account filters from URL

    const selectedCategories = Array.from(document.getElementById('categoryFilter').selectedOptions).map(option => option.value);
    selectedCategories.forEach(cat => queryParams.append('tx_category', cat));

    const selectedAccounts = Array.from(document.getElementById('accountFilter').selectedOptions).map(option => option.value);  // New: Get selected accounts
    selectedAccounts.forEach(acc => queryParams.append('account', acc));  // New: Append accounts to query

    window.location.search = queryParams.toString();
}

function updateBucketSize(size) {
    const params = new URLSearchParams(window.location.search);
    params.set('bucketSize', size);
    window.location.search = params.toString();
}