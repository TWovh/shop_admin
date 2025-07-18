document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".status-dropdown").forEach(function (select) {
        select.addEventListener("change", function () {
            const orderId = this.getAttribute("data-order-id");
            const newStatus = this.value;
            fetch("/admin/shop/order/update-status/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "X-CSRFToken": getCookie("csrftoken")
                },
                body: `order_id=${orderId}&new_status=${newStatus}`
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert(`Статус обновлён: ${data.status}`);
                } else {
                    alert(`Ошибка: ${data.error}`);
                }
            })
            .catch(error => {
                alert("Ошибка запроса");
                console.error(error);
            });
        });
    });
});

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
        const cookies = document.cookie.split(";");
        for (let cookie of cookies) {
            cookie = cookie.trim();
            if (cookie.startsWith(name + "=")) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
