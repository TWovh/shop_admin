(function($) {
  $(function() {
    console.log('orderitem_auto_price.js loaded with django.jQuery');

    // Обновление цены товара по select2
    $(document).on(
      'select2:select',
      'select[id^="id_order_items-"][id$="-product"]',
      function() {
        const $sel = $(this);
        const productId = $sel.val();
        const $row = $sel.closest('tr');
        const $price = $row.find('input[id$="-price"]');

        if (!productId) {
          $price.val('');
          updateTotal();
          return;
        }

        fetch(`/get-product-price/${productId}/`)
          .then(r => r.json())
          .then(json => {
            if (json.price !== undefined) {
              $price.val(json.price);
              updateTotal();
            }
          })
          .catch(err => console.error('Error fetching price:', err));
      }
    );

    // События для пересчёта суммы
    $(document).on('input', 'input[id$="-quantity"], input[id$="-price"]', function() {
      updateTotal();
    });

    // Добавим HTML для итоговой суммы
    function insertTotalField() {
      if ($('#order-total-row').length > 0) return;

      const $table = $('table#order_items-group');
      const $tfoot = $('<tfoot></tfoot>');
      const $tr = $('<tr id="order-total-row"><td colspan="10" style="text-align: right; font-weight: bold; padding: 10px;">Итого: <span id="order-total">0.00</span> грн</td></tr>');

      $tfoot.append($tr);
      $table.append($tfoot);
    }

    // Обновление итоговой суммы
    function updateTotal() {
      let total = 0;

      $('tr.dynamic-order_items').each(function() {
        const quantity = parseFloat($(this).find('input[id$="-quantity"]').val()) || 0;
        const price = parseFloat($(this).find('input[id$="-price"]').val()) || 0;
        total += quantity * price;
      });

      $('#order-total').text(total.toFixed(2));
    }

    // Ждём появления таблицы и вставим поле итого
    const interval = setInterval(() => {
      if ($('table#order_items-group').length > 0) {
        insertTotalField();
        updateTotal();
        clearInterval(interval);
      }
    }, 200);
  });
})(django.jQuery);
