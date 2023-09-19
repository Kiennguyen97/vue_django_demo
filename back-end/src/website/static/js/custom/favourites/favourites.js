// import axios from 'axios'

var csrftoken = this.$cookies.get("csrftoken");
const api = axios.create({
  baseUrl: "/",
  headers: {
    "Content-Type": "application/json",
    "X-CSRFTOKEN": csrftoken,
  },
});
var handle;

Vue.component("v-select", VueSelect.VueSelect);

Vue.component("favourites-item", {
  template: "#favourites-item-template",
  props: ["faves_item", "group", "show-quantities"],
  methods: {
    toggleNotesShow(faves_item) {
      this.$emit("toggle-notes-show", faves_item);
    },
    deleteItem(faves_item, group) {
      this.$emit("delete-item", faves_item, group);
    },
    addCart(faves_item) {
      this.$emit("add-cart", faves_item);
    },
    qtyChange(faves_item) {
      this.$emit("qty-change", faves_item);
    },
  },
});

var app = new Vue({
  el: "#vue-app",
  data: {
    listRename: "",
    userName: "",
    ref: "",
    favouritesName: "",
    favouritesUuid: "test",
    favouritesLists: [{ name: "test", value: "123", uuid: 30 }],
    isLoading: true,
    createList: true,
    newListName: "",
    showQuantities: false,
    hasSetDefault: false,
    files: "",
    favouritesData: {
      uuid: 1,
      name: "",
      sequence: 1,
      fave_groups: [
        {
          uuid: 1,
          name: "",
          sequence: 1,
          show_rename: false,
          fave_items: [
            {
              uuid: "1",
              product_sku: "1",
              product_name: "",
              price: "",
              product_img: "",
              max_qty: "",
              min_qty: "",
              carton_qty: 0,
              note: "",
              qty_order: "",
              qty: "",
              show_note: false,
            },
          ],
        },
      ],
      draggable: window["vuedraggable"],
    },
    fields_map: [
      "Code",
      "Description",
      "Price",
      "Maximum",
      "Current",
      "Required",
    ],
  },
  beforeMount() {
    const settings = localStorage.getItem("favouritesListShowQuantities");
    if (settings) {
      if (settings === "true") {
        this.showQuantities = true;
      } else {
        this.showQuantities = false;
      }
    }
  },
  methods: {
    toggleQuantities() {
      this.showQuantities = !this.showQuantities;

      if (this.showQuantities === true) {
        localStorage.setItem("favouritesListShowQuantities", "true");
      } else {
        localStorage.setItem("favouritesListShowQuantities", "false");
      }
    },
    setDefaultList() {
      const userId = document.getElementById("user-id").dataset.user;
      const key = "defaultList#" + userId;

      localStorage.setItem(key, this.favouritesData.uuid);
      this.hasSetDefault = true;
    },

    async getFavouritesData(uuid = false) {
      try {
        let fave_url = "";
        if (uuid == false) {
          fave_url = "/favourites/favourite/";
        } else {
          fave_url = "/favourites/favourite/" + uuid;
        }

        let response = await fetch(fave_url);
        let data = await response.json();
        // console.log(data)
        this.userName = data.userName;
        this.ref = data.ref;
        this.favouritesData = data?.favouritesData;
        this.favouritesName = data?.favouritesData?.name;
        this.favouritesUuid = data?.favouritesData?.uuid;
        this.favouritesLists = data?.favouritesLists;

        this.isLoading = false;
        this.hasSetDefault = false;
      } catch (err) {
        console.log(err);
      }
    },
    async addCart(item) {
      item.qty_order = item.qty_order ? parseInt(item.qty_order) : 1;
      if (item.qty_order > 0) {
        //hanđle loading btn
        item.cart_adding = true;

        api
          .post("/api/cart-items/", {
            product_price: item.price,
            product_quantity: item.qty_order,
            product_sku: item.product_id__sku,
          })
          .then((response) => {
            if (response.status == 201) {
              item.cart_adding = false;
              item.cart_added = true;
            }
          });
      }
    },
    async updateItem(uuid, action, value) {
      if (Number.isNaN(value.max_qty) || Number.isNaN(value.min_qty)) {
        console.log("invaid input");
        return;
      }
      // update specific line item
      api.post("/favourites/favourite/item", {
        uuid: uuid,
        action: action,
        value: value,
      });
    },
    async qtyChange(item) {
      self = this;

      qty_min = item.min_qty ? parseInt(item.min_qty) : 0;
      qty_max = item.max_qty ? parseInt(item.max_qty) : 0;

      qty = item.max_qty - item.min_qty;

      if ((item.max_qty != "") & (item.min_qty != "")) {
        item.qty_order = qty;
      }

      data = {};
      if (item.max_qty != "") {
        data["max_qty"] = parseInt(item.max_qty);
      }
      if (item.min_qty != "") {
        data["min_qty"] = parseInt(item.min_qty);
      }
      if (parseInt(qty) > 0) {
        data["qty_order"] = parseInt(qty);
        item.qty = qty;
      }
      if (typeof handler !== "undefined") {
        clearTimeout(handler);
        handler = setTimeout(
          () => self.updateItem(item.uuid, "update", data),
          500
        );
      } else {
        handler = setTimeout(
          () => self.updateItem(item.uuid, "update", data),
          500
        );
      }
    },

    selectFavouritesList(evt) {
      this.isLoading = true;
      if (evt !== null) {
        console.log(evt.uuid);
        this.getFavouritesData(evt.uuid);
      } else {
        console.log("Delete Favourire: " + this.favouritesUuid);
        fave_url = "/favourites/favourite/" + this.favouritesUuid;
        api.delete(fave_url).then((response) => {
          if (response.status == 200) {
            fav_list = this.favouritesLists[0];
            if (typeof fav_list !== "undefined") {
              this.getFavouritesData(fav_list.uuid);
            } else {
              this.getFavouritesData();
            }
          }
        });
      }
    },

    dragGroup(evt) {
      console.log(
        `item ${evt.item.childNodes[0].id} resides at index ${evt.newIndex}`
      );
      let uuid = evt.item.childNodes[0].id;
      api.post("/favourites/favourite/group", {
        uuid: uuid,
        action: "resequence",
        value: evt.newIndex, // zero indexed in python
      });
    },
    dragItem(evt) {
      console.log(
        `item ${evt.item.id} now resides at index ${evt.newIndex} on group ${evt.to.parentElement.id}`
      );
      api.post("/favourites/favourite/item", {
        uuid: evt.item.id,
        action: "resequence",
        group_uuid: evt.to.parentElement.id,
        value: evt.newIndex,
      });
    },

    closeCreateList() {
      $("#createList").modal("hide");
    },
    closeImportFavList() {
      $("#import-fav-list").modal("hide");
    },
    toggleCreateList() {
      $("#createList").modal("show");
    },
    toggleRenameList() {
      $("#renameList").modal("show");
    },
    closeRenameList() {
      $("#renameList").modal("hide");
    },
    toggleDeleteList() {
      $("#deleteList").modal("show");
    },
    closeDeleteList() {
      $("#deleteList").modal("hide");
    },
    updateListName() {
      console.log(this.listRename);
      let newName = this.listRename;
      let uuid = this.favouritesData.uuid;

      api
        .post("/favourites/favourite/" + uuid + "/", {
          uuid: uuid,
          name: newName,
          action: "rename_list",
        })
        .then((response) => {
          if (response.status == 200) {
            this.favouritesData.name = newName;
            this.favouritesName = newName;
            this.closeRenameList();
          } else {
            alert(
              "Error Occured. Can not rename list right now, please reload the page."
            );
          }
        });
    },
    async updateListDelete() {
      let uuid = this.favouritesData.uuid;
      api
        .delete("/favourites/favourite/" + uuid + "/", {
          uuid,
          action: "delete",
          value: "delete",
        })
        .then((response) => {
          if (
            response.status == 200 ||
            response.status == 202 ||
            response.status == 204
          ) {
            const userId = document.getElementById("user-id").dataset.user;
            const key = "defaultList#" + userId;
            const defaultList = localStorage.getItem(key);
            if (defaultList) {
              // check if the delete list was the default, if so delete from local storage
              if (defaultList === uuid) {
                localStorage.removeItem(key);
              }
            }
            this.getFavouritesData();
          } else {
            alert(
              "Error Occured. Can not delete list right now, please reload the page"
            );
          }
        })
        .finally(() => {
          this.closeDeleteList();
        });
    },
    toggleCreateListUpload() {
      if (!$('#import-fav-list input[name="csrfmiddlewaretoken"]').length) {
        $("#form-import-favourite-list").append(
          $('input[name="csrfmiddlewaretoken"]')
        );
      }
      form = $("#form-import-favourite-list");
      target_err = form.find('input[name="file"]').next();
      target_err.hide();
      $("#import-fav-list").modal("show");
    },
    createNewList() {
      console.log(`creating list with ${this.newListName}`);
      console.log(this.newListName);
      api
        .post("/favourites/favourite/", {
          name: this.newListName,
          action: "create_list",
        })
        .then((response) => {
          if (response.status == 200) {
            //this.toggleCreateList();
            this.getFavouritesData();
          } else {
            alert(
              "Error Occured. Can not create list right now, please reload the page."
            );
          }
          this.newListName = "";
        });
    },
    previewFile(event) {
      target_err = $(event.target).next();
      target_err.hide();
    },

    importFavList() {
      form = $("#form-import-favourite-list");
      target_err = form.find('input[name="file"]').next();
      target_err.hide();
      file = form.find('input[name="file"]').get(0).files[0];
      if (typeof file == "undefined") {
        target_err.show();
      } else {
        this.isLoading = true;
        form.submit();
      }
    },
    closeImportFavouriteList() {
      $("#import-fav-list").modal("hide");
    },

    toggleNotesShow(faves_item) {
      this.$emit("toggle-notes-show", faves_item);
      if (faves_item.show_note == true) {
        // update it to the server if it's currently open
        this.updateItem(faves_item.uuid, "note", faves_item.note);
        faves_item.show_note = false;
      } else {
        faves_item.show_note = true;
      }
    },

    toggleRenameGroupShow(group) {
      if (group.show_rename == true) {
        group.show_rename = false;
      } else {
        group.show_rename = true;
      }
    },
    renameGroupSave(group, groupIndex) {
      let newName = $(event.target).siblings("input").val();
      let uuid = group.uuid;

      api
        .post("/favourites/favourite/group", {
          uuid: uuid,
          action: "rename_list",
          value: newName,
        })
        .then((response) => {
          if (response.status == 200) {
            this.favouritesData.fave_groups[groupIndex].name = newName;
            this.toggleRenameGroupShow(group);
          } else {
            alert(
              "Error Occured. Can not rename group right now, please reload the page."
            );
          }
        });
    },
    async createGroup(favouritesUuid) {
      console.log("creating group with uuid" + favouritesUuid);
      this.loading = true;
      api
        .post("/favourites/favourite/group", {
          uuid: "",
          action: "create",
          value: favouritesUuid,
        })
        .then((response) => {
          if (
            response.status == 200 ||
            response.status == 202 ||
            response.status == 204
          ) {
            let data = response.data;
            this.favouritesData.fave_groups.push({
              uuid: data.uuid,
              name: data.name,
              show_rename: false,
              fave_items: [],
            });
          } else {
            alert(
              "Error Occured. Can not delete group right now, please reload the page"
            );
          }
        });
    },
    async deleteGroup(group, groupIndex) {
      api
        .post("/favourites/favourite/group", {
          uuid: group.uuid,
          action: "delete",
          value: "delete",
        })
        .then((response) => {
          if (
            response.status == 200 ||
            response.status == 202 ||
            response.status == 204
          ) {
            this.favouritesData.fave_groups.splice(groupIndex, 1);
          } else {
            alert(
              "Error Occured. Can not delete group right now, please reload the page"
            );
          }
        });
    },
    async deleteItem(faves_item, group) {
      api
        .post("/favourites/favourite/item", {
          uuid: faves_item.uuid,
          action: "delete",
          value: "delete",
        })
        .then((response) => {
          if (
            response.status == 200 ||
            response.status == 202 ||
            response.status == 204
          ) {
            // this.favouritesData.fave_groups[
            //   group.sequence - 1
            // ].fave_items.splice(faves_item.sequence - 1, 1);
            this.getFavouritesData();
          } else {
            alert(
              "Error Occured. Can not delete item right now, please reload the page"
            );
          }
        });
    },
    async exportFavList() {
      //  www.npmjs.com/package/write-excel-file

      const fileName = `favourites list - ${this.favouritesData.name}.xlsx`;
      const compName =
        document.getElementById("company-name").dataset.companyName;
      const compID = document.getElementById("company-id").dataset.companyId;

      const emptyCell = { value: "" };
      const emptyRow = [
        emptyCell,
        emptyCell,
        emptyCell,
        emptyCell,
        emptyCell,
        emptyCell,
      ];

      const HEADER_ROW = [
        {
          value: "Customer",
          fontWeight: "bold",
        },
        {
          value: compName,
        },
        emptyCell,
        emptyCell,
        {
          value: compID !== "" ? "Ref" : "",
          fontWeight: "bold",
        },
        {
          value: compID,
        },
      ];

      const row_1_base_styles = {
        color: "#FFFFFF",
        backgroundColor: "#000000",
        fontWeight: "bold",
        height: 20,
        alignVertical: "center",
      };

      const DATA_ROW_1 = [
        {
          value: "Code",
          ...row_1_base_styles,
        },
        {
          value: "Description",
          ...row_1_base_styles,
        },
        {
          value: "Price",
          ...row_1_base_styles,
        },
        {
          value: "Maximum",
          ...row_1_base_styles,
        },
        {
          value: "Current",
          ...row_1_base_styles,
        },
        {
          value: "Required",
          ...row_1_base_styles,
        },
      ];

      const baseData = [HEADER_ROW, emptyRow, DATA_ROW_1];

      const data = this.prepareFavsData(baseData);

      const columns = [
        { width: 10 },
        { width: 50 },
        { width: 10 },
        { width: 10 },
        { width: 10 },
        { width: 10 },
      ];

      await writeXlsxFile(data, { columns, fileName });
    },
    prepareFavsData(baseData) {
      const data = baseData;

      const border = {
        bottomBorderColor: "#000000",
        bottomBorderStyle: "thin",
      };

      const emptyGreyCell = {
        value: "",
        backgroundColor: "#C0C0C0",
      };

      this.favouritesData.fave_groups.forEach((group) => {
        const row = [
          {
            value: group.name,
            color: "#000000",
            backgroundColor: "#C0C0C0",
            fontWeight: "bold",
            span: 6,
            height: 20,
            alignVertical: "center",
            leftBorderColor: "#000000",
            leftBorderStyle: "thin",
            ...border,
          },
          emptyGreyCell,
          emptyGreyCell,
          emptyGreyCell,
          emptyGreyCell,
          {
            rightBorderColor: "#000000",
            rightBorderStyle: "thin",
            ...emptyGreyCell,
          },
        ];

        data.push(row);

        group.fave_items.forEach((item) => {
          const row = [
            {
              value: item.product_id__sku,
              leftBorderColor: "#000000",
              leftBorderStyle: "thin",
              ...border,
            },
            {
              value: item.product_id__name,
              ...border,
            },
            {
              value: `$${item.price}`,
              ...border,
            },
            {
              value: item.max_qty,
              type: Number,
              ...border,
            },
            {
              value: item.min_qty,
              type: Number,
              ...border,
            },
            {
              value: item.qty_order,
              type: Number,
              rightBorderColor: "#000000",
              rightBorderStyle: "thin",
              ...border,
            },
          ];

          data.push(row);
        });
      });

      return data;
    },
  },
  mounted() {
    const userId = document.getElementById("user-id").dataset.user;
    const key = "defaultList#" + userId;
    const defaultList = localStorage.getItem(key);
    if (defaultList) {
      this.getFavouritesData(defaultList);
    } else {
      this.getFavouritesData();
    }
  },
});
