$(function () {
  jQuery(document).ready(function () {
    // Click search icon add class body
    $(".header-search-wrap .header-search-icon").click(function () {
      $("body").toggleClass("search-open-form");
    });

    // push list fav group to dropdown when loaded
    function getFavouritesData() {
      $.ajax({
        url: "/favourites/favourite/",
        method: "GET",
        async: true,
      }).done(function (data) {
        const dataCopy = [...data.favouritesGroups];
        dataCopy.sort(
          (a, b) =>
            a.favourites_list__name.localeCompare(b.favourites_list__name) ||
            a.name.localeCompare(b.name)
        );

        try {
          $.each(dataCopy, function (index, group) {
            let groupItem =
              '<li class="group-item" data-uuid="' +
              group.uuid +
              '">' +
              group.name +
              "</li>";
            $("#group-favouries-select").append(
              $("<option>", {
                value: group.uuid,
                text: group.favourites_list__name + " - " + group.name,
              })
            );
            if (
              $("#group-faveries-select").siblings(".nice-select").length > 0
            ) {
              $("#group-faveries-select")
                .siblings(".nice-select")
                .find(".list")
                .append(groupItem);
              if (index == 0) {
                $("#group-faveries-select")
                  .siblings(".nice-select")
                  .find(".current")
                  .text(group.name);
              }
            }
          });
        } catch (error) {
          console.log(error);
        }
      });
    }
    getFavouritesData();

    $('button[data-action="add-prod-to-group"]').on("click", function (e) {
      let groupUuid = $("#group-favouries-select").val();
      let modal = $(".product-detail .modal");
      let product_sku = $("#product-details-add-to-cart")
        .parents(".modal-product-info")
        .find(".product-sku")
        .val();

      $.ajax({
        url: "/favourites/favourite/item",
        method: "POST",
        async: true,
        data: {
          action: "add",
          value: product_sku,
          uuid: groupUuid,
        },
      }).done(function (data) {
        $(".page-wrapper-message").html(data.message_html);
        modal.hide();
        $(".modal-backdrop").removeClass("show");
        $(".modal-backdrop").hide();
        $("body").removeClass("modal-open");
      });
    });

    /**
     * Event show modal
     */
    $('button[data-role="modal-favourites"]').on("click", function () {
      let product_sku = $(this)
        .parents(".modal-product-info")
        .find(".product-sku")
        .val();
      $("#modal-favourites").find('input[name="product-sku"]').val(product_sku);
      $("#modal-favourites").modal("show");
    });
    /**
     * Event hide modal
     */
    $('#modal-favourites button[data-dismiss="modal"]').on(
      "click",
      function () {
        $("#modal-favourites").modal("hide");
      }
    );

    /**
     * Event add product to Fav on list product
     */
    $('button[data-action="add-list-prod-to-group"]').on("click", function (e) {
      let groupUuid = $("#group-favouries-select").val();
      let modal = $("#modal-favourites");
      let product_sku = $(this)
        .parents("#modal-favourites")
        .find('input[name="product-sku"]')
        .val();
      $.ajax({
        url: "/favourites/favourite/item",
        method: "POST",
        async: true,
        data: {
          action: "add",
          value: product_sku,
          uuid: groupUuid,
        },
      }).done(function (response) {
        $(".page-wrapper-message").html(response.message_html);
        $("#modal-favourites").modal("hide");
      });
    });
  });
});
