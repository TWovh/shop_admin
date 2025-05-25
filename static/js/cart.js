class CartService {
    constructor() {
        this.baseUrl = '/api/cart';
    }

    async getCart() {
        const response = await authService.authFetch(this.baseUrl + '/');
        return response.json();
    }

    async addToCart(productId) {
        const response = await authService.authFetch(this.baseUrl + '/add/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ product_id: productId })
        });
        return response.json();
    }
}

const cartService = new CartService();

// Пример использования
async function loadCart() {
    try {
        const cart = await cartService.getCart();
        console.log('Cart items:', cart.items);
    } catch (error) {
        console.error('Ошибка загрузки корзины:', error);
    }
}