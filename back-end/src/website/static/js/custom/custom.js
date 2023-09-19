$(function () {
  $(document).ready(function () {
    // Function owlCarousel
    customOwl(".slider-home .owl-carousel", true, true, false, 10, 1, 1, 1);
    customOwl(
      ".hp-featured-products .owl-carousel",
      true,
      true,
      false,
      20,
      1,
      2,
      4
    );
    customOwl(
      ".home_help_section .owl-carousel",
      true,
      true,
      false,
      10,
      1,
      3,
      4
    );
    customOwl(".hp-our-brands .owl-carousel", true, true, false, 10, 1, 4, 5);
    customOwl(
      ".service-help-section .owl-carousel",
      false,
      true,
      false,
      0,
      1,
      2,
      4
    );
    customOwl(
      ".service-recent-blog-section .owl-carousel",
      true,
      true,
      false,
      20,
      1,
      2,
      4
    );
    customOwl(
      ".recent-post-section .owl-carousel",
      false,
      true,
      false,
      20,
      1,
      2,
      4
    );
    customOwl(
      ".meet-expert-testimonial .owl-carousel",
      true,
      true,
      false,
      0,
      1,
      1,
      1
    );
    customOwl(
      ".publication-resource-video .owl-carousel",
      true,
      true,
      false,
      20,
      1,
      2,
      4
    );

    customOwl(
      ".testimonial-video-slider .owl-carousel",
      true,
      true,
      false,
      20,
      1,
      2,
      4
    );

    // toggle menu footer
    $("#footer-main .footer-content h4").click(function () {
      $(this).parent().toggleClass("active");
    });

    // toggle menu on category page
    $(".sidebar-main .block-content > ul > .level0 > a > .opener").click(
      function (e) {
        e.preventDefault();
        $(this).parents("li.level0").toggleClass("active");
      }
    );
    $(".level0 > ul > li > a > .opener").click(function (e) {
      e.preventDefault();
      $(this).parents("li.level1").toggleClass("active");
    });
  });
  function customOwl(item, loop, dots, nav, marginCustom, item1, item2, item3) {
    $(item).owlCarousel({
      loop: loop,
      margin: marginCustom,
      nav: nav,
      autoplay: true,
      autoplayHoverPause: true,
      responsive: {
        0: {
          items: item1,
        },
        575: {
          items: item2,
        },
        768: {
          items: item2,
        },
        1000: {
          items: item3,
        },
      },
    });
  }
  /**
   * Check account left sidebar menu link active
   * -------------------------------------------
   */
  $(".account .nav-items a").each(function () {
    if ($(this).attr("href") === window.location.pathname) {
      $(".account .nav-items a").removeClass("active");
      $(this).addClass("active");
    }
  });
  /**
   * Check active order history link at order view page
   * -------------------------------------------
   */
  var viewPath = window.location.pathname;
  var arrViewPath = viewPath.split("/");

  if (arrViewPath[2] === "order-view") {
    $(".account .nav-items a").removeClass("active");
    $('.account .nav-items a[data-cy="order-history-nav-link"]').addClass(
      "active"
    );
  }

  if (arrViewPath[2] === "add-address") {
    $(".account .nav-items a").removeClass("active");
    $('.account .nav-items a[data-cy="address-book-nav-link"]').addClass(
      "active"
    );
  }

  if (arrViewPath[2] === "update_address") {
    $(".account .nav-items a").removeClass("active");
    $('.account .nav-items a[data-cy="address-book-nav-link"]').addClass(
      "active"
    );
  }

  /**
   * Change nav title mobile
   * -------------------------------------------
   */

  $(".account .nav-title").text($(".account .nav-items a.active").text());

  $("body").on("click", ".menu-account-sidebar .nav-title", function () {
    if ($(window).width() < 992) {
      if ($(this).parents(".menu-account-sidebar").hasClass("open")) {
        $(this).parents(".menu-account-sidebar").find(".nav-items").slideUp();
        $(this).parents(".menu-account-sidebar").removeClass("open");
      } else {
        $(".nav-items").slideUp();
        $(".menu-account-sidebar").removeClass("open");

        $(this).parents(".menu-account-sidebar").find(".nav-items").slideDown();
        $(this).parents(".menu-account-sidebar").addClass("open");
      }
    }
  });
  /**
   * Show/Hide Quantity in Favourites Page
   * -------------------------------------------
   */
  $(".show-quantities span").click(function () {
    $("body").toggleClass("status-qty");
  });
  /**
   * Show/Hide table in Favourites Page
   * -------------------------------------------
   */
  // $(".favourite-list thead tr th.action .fa-caret-down").click(function () {
  //   $(this).toggleClass("status-table");
  // });

  /**
   * Public function set height item
   * -------------------------------------------
   */
  function setHeight(item) {
    if (item.length > 0) {
      // console.log(item);
      var maxHeightElement = 0;
      item.each(function () {
        if ($(this).height() > maxHeightElement) {
          maxHeightElement = $(this).height();
        }
      });
      if (maxHeightElement > 0) {
        item.height(maxHeightElement);
      }
      $(window).resize(function () {
        item.css("height", "");
        var maxHeightElement = 0;
        item.each(function () {
          if ($(this).height() > maxHeightElement) {
            maxHeightElement = $(this).height();
          }
        });
        if (maxHeightElement > 0) {
          item.height(maxHeightElement);
        }
      });
    }
  }

  setHeight(
    $(".sub-categories-grid .sub-categories-items .sub-category-item-details")
  );
});


function onSubmitSubscribe() {
  var site_key = document.getElementById("subscribe-submit").getAttribute("data-sitekey");
  if (site_key === null) {
    var form = document.getElementById("newsletter-validate-detail");
    var reportValidity = form.reportValidity();
    // Then submit if form is OK.
    if (reportValidity) {
      form.submit();
    }
  } else {
    grecaptcha.ready(function () {
      grecaptcha.execute(site_key, {action: 'submit'}).then(function (token) {
        var g_recaptcha_el = document.getElementById('newsletter-g-recaptcha-response');
        g_recaptcha_el.value = token;
        var form = document.getElementById("newsletter-validate-detail");
        var reportValidity = form.reportValidity();
        // Then submit if form is OK.
        if (reportValidity) {
          form.submit();
        }
      });
    });
  }
};

// Ajax submit newsletter
function onSubmitSubscribeForm(e) {
    let post_url = "/subscribe/",
      form = document.getElementById("newsletter-validate-detail"),
      error_selector = document.getElementById("subscribe-error"),
      success_selector = document.getElementById("subscribe-success"),
      formdata = new FormData(form),
      email = formdata.get("email"),
      data_post = {
        email_address: formdata.get("email"),
        "g-recaptcha-response": e,
      };
    error_selector.innerHTML = "";
    if (email == "") {
      error_selector.innerHTML = "This field is required";
      success_selector.innerHTML = "";
      return false;
    } else {
      const xhttp = new XMLHttpRequest();
      xhttp.open("POST", post_url, true);
      xhttp.setRequestHeader("Content-type", "application/json; charset=UTF-8");
      xhttp.setRequestHeader(
        "X-CSRFTOKEN",
        document.querySelector("[name=csrfmiddlewaretoken]").value
      );
      xhttp.setRequestHeader("x-Requested-With", "XMLHttpRequest");
      xhttp.send(JSON.stringify(data_post));
      xhttp.onload = function () {
        let res = JSON.parse(xhttp.response);
        if (res.is_error) {
          error_selector.innerHTML = res.msg;
          success_selector.innerHTML = "";
        } else {
          error_selector.innerHTML = "";
          success_selector.innerHTML = res.msg;
        }
      };
    }
  }
