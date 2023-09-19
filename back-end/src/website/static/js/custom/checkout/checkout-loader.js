$(function () {
  let shipping_step = $(".shipping-address-wrapper"),
    billing_step = $(".billing-address-wrapper"),
    order_info_step = $(".order-info-wrapper"),
    payment_step = $(".payment-method-wrapper"),
    step_checkout = $(".step-checkout"),
    btn_next = $('[data-role="btn-next"]');

  shipping_step.find('[data-role="title"]').click(function () {
    step_checkout.removeClass("opener");
    shipping_step.addClass("opener");
  });
  billing_step.find('[data-role="title"]').click(function () {
    step_checkout.removeClass("opener");
    billing_step.addClass("opener");
  });
  order_info_step.find('[data-role="title"]').click(function () {
    step_checkout.removeClass("opener");
    order_info_step.addClass("opener");
  });
  payment_step.find('[data-role="title"]').click(function () {
    step_checkout.removeClass("opener");
    payment_step.addClass("opener");
  });

  btn_next.click(function () {
    let step = $(this).data("step");
    step_checkout.removeClass("opener");
    $("." + step).addClass("opener");
  });
});
