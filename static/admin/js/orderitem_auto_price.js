(function($) {
  $(function() {
    console.log('orderitem_auto_price.js loaded with django.jQuery');

    $(document).on(
      'select2:select',
      'select[id^="id_order_items-"][id$="-product"]',
      function() {
        const $sel = $(this);
        const productId = $sel.val();
        const $row = $sel.closest('tr');
        const $price = $row.find('input[id$="-price"]');

        console.log('Select2: selected product ID =', productId);

        if (!productId) {
          $price.val('');
          return;
        }

        fetch(`/get-product-price/${productId}/`)
          .then(r => r.json())
          .then(json => {
            console.log('Price fetched:', json);
            if (json.price !== undefined) {
              $price.val(json.price);
            }
          })
          .catch(err => console.error('Error fetching price:', err));
      }
    );
  });
})(django.jQuery);
