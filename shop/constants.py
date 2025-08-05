"""
Константы для приложения shop
"""

# Статусы заказов
ORDER_STATUS_PENDING = 'pending'
ORDER_STATUS_PROCESSING = 'processing'
ORDER_STATUS_COMPLETED = 'completed'
ORDER_STATUS_CANCELLED = 'cancelled'

ORDER_STATUS_CHOICES = [
    (ORDER_STATUS_PENDING, 'В ожидании'),
    (ORDER_STATUS_PROCESSING, 'В обработке'),
    (ORDER_STATUS_COMPLETED, 'Завершён'),
    (ORDER_STATUS_CANCELLED, 'Отменён'),
]

# Статусы платежей
PAYMENT_STATUS_UNPAID = 'unpaid'
PAYMENT_STATUS_PAID = 'paid'
PAYMENT_STATUS_PENDING = 'pending'
PAYMENT_STATUS_REFUNDED = 'refunded'

PAYMENT_STATUS_CHOICES = [
    (PAYMENT_STATUS_UNPAID, 'Не оплачено'),
    (PAYMENT_STATUS_PAID, 'Оплачено'),
    (PAYMENT_STATUS_PENDING, 'Ожидает'),
    (PAYMENT_STATUS_REFUNDED, 'Возврат'),
]

# Типы доставки
DELIVERY_TYPE_PREPAID = 'prepaid'
DELIVERY_TYPE_COD = 'cod'

DELIVERY_TYPE_CHOICES = [
    (DELIVERY_TYPE_PREPAID, 'Оплата онлайн'),
    (DELIVERY_TYPE_COD, 'Наложенный платеж'),
]

# Методы доставки
DELIVERY_METHOD_NOVA_POSHTA = 'nova_poshta'
DELIVERY_METHOD_SELF_PICKUP = 'self_pickup'
DELIVERY_METHOD_OTHER = 'other'

DELIVERY_METHOD_CHOICES = [
    (DELIVERY_METHOD_NOVA_POSHTA, 'Новая Почта'),
    (DELIVERY_METHOD_SELF_PICKUP, 'Самовывоз'),
    (DELIVERY_METHOD_OTHER, 'Другое'),
]

# Платежные системы
PAYMENT_SYSTEM_STRIPE = 'stripe'
PAYMENT_SYSTEM_PAYPAL = 'paypal'
PAYMENT_SYSTEM_PORTMONE = 'portmone'
PAYMENT_SYSTEM_LIQPAY = 'liqpay'
PAYMENT_SYSTEM_FONDY = 'fondy'
PAYMENT_SYSTEM_MANUAL = 'manual'

PAYMENT_SYSTEM_CHOICES = [
    (PAYMENT_SYSTEM_STRIPE, 'Stripe'),
    (PAYMENT_SYSTEM_PAYPAL, 'PayPal'),
    (PAYMENT_SYSTEM_PORTMONE, 'Portmone'),
    (PAYMENT_SYSTEM_LIQPAY, 'LiqPay'),
    (PAYMENT_SYSTEM_FONDY, 'Fondy'),
]

# Роли пользователей
USER_ROLE_ADMIN = 'ADMIN'
USER_ROLE_STAFF = 'STAFF'
USER_ROLE_USER = 'USER'

USER_ROLE_CHOICES = [
    (USER_ROLE_ADMIN, 'Администратор'),
    (USER_ROLE_STAFF, 'Менеджер'),
    (USER_ROLE_USER, 'Пользователь'),
]

# Webhook события
WEBHOOK_EVENTS = {
    'stripe': ['checkout.session.completed'],
    'paypal': ['PAYMENT.CAPTURE.COMPLETED', 'CHECKOUT.ORDER.APPROVED'],
    'fondy': ['approved'],
    'liqpay': ['success'],
    'portmone': ['success'],
}

# Таймауты для API запросов
API_TIMEOUT = 10  # секунды

# Лимиты для API
MAX_ORDER_ITEMS = 50
MAX_CART_ITEMS = 20
MIN_ORDER_AMOUNT = 1.0  # минимальная сумма заказа в гривнах

# Настройки для Nova Poshta
NOVA_POSHTA_DEFAULT_WEIGHT = 1.0  # кг
NOVA_POSHTA_DEFAULT_SEATS = 1
NOVA_POSHTA_DEFAULT_PHONE = '0500000000'

# Настройки для email
EMAIL_SUBJECT_PAYMENT_SUCCESS = "Оплата заказа #{order_id} подтверждена"
EMAIL_SUBJECT_ORDER_CREATED = "Заказ #{order_id} создан"

# Настройки для логирования
LOG_PAYMENT_PREFIX = "PAYMENT"
LOG_NOVA_POSHTA_PREFIX = "NOVA_POSHTA"
LOG_WEBHOOK_PREFIX = "WEBHOOK" 