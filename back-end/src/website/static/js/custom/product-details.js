var app = new Vue({
    el: "#vue-app",
    data: {
        config: context,
        option_selected: {},
        modal: "",
        clickCount: 0,
        items: [],
        firstChoose: 0,
        data_cart: {},
        default_price: 0,
        loading: false,
        list_selected:[],
        display_sku: "",
    },
    methods: {
        get_product_sku() {
            let product_sku = this.get_data_option_size().product_sku;
            product_sku = this.process_options(this.config.options.RECTANGLE, product_sku);
            product_sku = this.process_options(this.config.options.RADIO, product_sku);
            this.display_sku = product_sku.trim();
            return this.display_sku;
        },

        process_options(option, product_sku) {
            let self = this;
            Object.values(option).forEach(function (opt) {
                if (opt.default_option_id !== null && opt.default_option && opt.default_option.active && opt.active && opt.type != "SIZE") {
                    product_sku += " " + opt.default_option.sku_addition;
                }
            });
            return product_sku;
        },

        get_dimensions() {
            let dimensions = this.get_data_option_size().dimensions;
            return dimensions;
        },

        get_data_option_size() {
            let dimensions = this.config.dimension;
            let product_sku = this.config.display_sku;
            if (this.config.options.default_size_choice == "RECTANGLE") {
                var data = this.process_option_size(dimensions, product_sku, this.config.options.RECTANGLE)
            } else {
                var data = this.process_option_size(dimensions, product_sku, this.config.options.RADIO)
            }
            return {
                dimensions: data.dimensions,
                product_sku: data.product_sku
            }
        },

        process_option_size(dimensions, product_sku, options) {
            let self = this;
            Object.values(options).forEach(function (opt) {
                if (opt.default_option_id !== null && opt.default_option && opt.default_option.active && opt.active && opt.type == "SIZE") {
                    dimensions = opt.default_option.dimension;
                    product_sku = product_sku.replace(self.config.display_sku, opt.default_option.sku_addition);
                }
            });
            return {
                dimensions: dimensions,
                product_sku: product_sku
            }
        },

        get_option_name(opt) {
            let opt_name = "";
            if (opt.default_option && opt.default_option.active) {
                opt_name = opt.default_option.name;
                if (opt.default_option.price > 0) {
                    opt_name += " (+$" + opt.default_option.price.toFixed(2) + ")"
                }
            }
            return opt_name;
        },
        get_o_name(o) {
            let opt_name = o.name
            if (o.price > 0) {
                opt_name += " (+$" + o.price.toFixed(2) + ")"
            }
            return opt_name;
        },
        get_default_option_name(o) {
            let opt_name = "";
            if (o.default_option.hasOwnProperty("id") && o.default_option.active) {
                opt_name = `${o.default_option.name}`
            }
            return opt_name;
        },
        openRectagleOption(opt) {
            if (opt) {
                this.clickCount++
            }
            let modal_el = document.getElementById("modal-" + opt.uuid);
            this.option_selected = opt;
            opt.open = true;
            this.modal = new bootstrap.Modal(modal_el);
            this.modal.show()
        },

        changeImage() {
            let self = this;
            let value_matching = '';
            let li;
            this.config.gallery.forEach(function (value) {
                if (value.sku_matching != ' ' && self.display_sku.includes(value.sku_matching) && value_matching.length < value.sku_matching.length) {
                    value_matching = value.sku_matching;
                    if (value.hide_thumbnail) {
                        self.replaceImage(value.image);
                    } else {
                        li = document.querySelector("[data-sku='" + value_matching + "']")
                    }
                }
            })
            if (li) {
                let slick = li.closest("div.slick-slide");
                if (slick) {
                    slick.click();
                }
            }
        },

        selectedOption(o, opt) {
            this.firstChoose = o.id;
            opt.default_option = o;
            this.reUpdateOption();
            this.reCalculatePrice();

            try {
                // Hide the modal
                this.modal.hide();
            } catch (err) {
                console.log(err)
            }

            // Set is_error to false and return true
            opt.is_error = false;
            return true;
        },

        updateOption() {
            let list_checked = [];
            let self = this;
            if (!this.config.options.no_depend) {
                this.config.options.product_option_not_depend.forEach(function (opt, index) {
                    list_checked = self.processUpdateProductOption(self, opt, list_checked, false)
                })

                list_checked = [];
                this.config.options.product_option_depend.forEach(function (opt, index) {
                    list_checked = self.processUpdateProductOption(self, opt, list_checked, true)
                })

                list_checked = [];
                self.config.options.option_not_depend.forEach(function (opt, index) {
                    list_checked = self.processUpdateOption(self, opt, list_checked, false)
                })

                list_checked = [];
                self.config.options.option_depend.forEach(function (opt, index) {
                    list_checked = self.processUpdateOption(self, opt, list_checked, true)
                })
                self.reUpdateDefaultOption();
            }
        },

        reUpdateDefaultOption() {
            let self = this;
            self.processUpdateDefaultOption(self.config.options.RECTANGLE, "RECTANGLE");
            self.processUpdateDefaultOption(self.config.options.RADIO, "RADIO");
        },

        processUpdateDefaultOption(options, type) {
            let self = this;
            Object.values(options).forEach(function (opt) {
                if (opt.default_option_id !== null) {
                    let index_option = self.config.options.list_index.option_depend[opt.uuid].options[opt.default_option_id];
                    if (index_option !== undefined){
                        opt.default_option = opt.options[index_option];
                    }
                }
            });
        },

        processUpdateProductOption(self, opt, list_checked, active_status) {
            let option_depend_id = parseInt(Object.keys(opt)[0]);
            let product_option_type = Object.keys(Object.values(opt)[0])[0];
            let product_option_id = parseInt(Object.values(Object.values(opt)[0])[0]);
            let index_product_option = self.config.options.list_index[product_option_type][product_option_id];
            let product_option = self.config.options[product_option_type][index_product_option];
            list_checked = self.processUpdate(self, product_option, list_checked, active_status, option_depend_id, product_option_id);
            return list_checked
        },

        processUpdateOption(self, opt, list_checked, active_status) {
            let option_depend_id = parseInt(Object.keys(opt)[0]);
            let product_option_type = Object.keys(Object.values(opt)[0])[0];
            let product_option_id = parseInt(Object.keys(Object.values(Object.values(opt)[0])[0])[0]);
            let option_id = parseInt(Object.values(Object.values(Object.values(opt)[0])[0])[0]);
            let index_product_option = self.config.options.list_index[product_option_type][product_option_id];
            let index_option = self.config.options.list_index.option_depend[product_option_id].options[option_id];
            let option = self.config.options[product_option_type][index_product_option].options[index_option];
            list_checked = self.processUpdate(self, option, list_checked, active_status, option_depend_id, option_id);
            return list_checked
        },

        processUpdate(self, opt, list_checked, active_status, depend_id, id) {
            if (list_checked.includes(id)) {
                return list_checked;
            }
            if (self.list_selected.includes(depend_id)) {
                list_checked.push(id);
                opt.active = active_status;
            } else {
                opt.active = !active_status;
            }
            return list_checked
        },

        reCalculatePrice() {
            this.config.price = this.default_price
            this.processPrices(this.config.options.RECTANGLE)
            this.processPrices(this.config.options.RADIO)
        },

        reUpdateOption() {
            this.list_selected = []
            this.processListSelected(this.config.options.RECTANGLE)
            this.processListSelected(this.config.options.RADIO)
            this.updateOption();
        },

        processListSelected(options) {
            let self = this;
            Object.values(options).forEach(function (opt) {
                // check type of != undefined
                if (opt.default_option_id !== null && opt.default_option) {
                    if (!self.list_selected.includes(opt.default_option.id) && !self.config.options.no_depend) {
                        self.list_selected.push(opt.default_option.id);
                    }
                }
            });
        },

        processPrices(options) {
            let self = this;
            Object.values(options).forEach(function (opt) {
                if (opt.default_option_id !== null && opt.default_option && opt.default_option.active && opt.active) {
                    self.config.price += opt.default_option.price
                }
            });
        },

        processAddToCart(option, data, is_pass) {
            Object.values(option).forEach(function (opt, index) {
                if (opt.default_option_id !== null && opt.default_option && opt.default_option.active && opt.active) {
                    opt.is_error = false;
                    data["cart_options"].push(
                        {
                            productoption_id: opt.uuid,
                            option_id: opt.default_option_id
                        }
                    )
                } else {
                    if (opt.required && opt.active) {
                        is_pass = false;
                        opt.is_error = true;
                    }
                }
            })
            return {data, is_pass}
        },

        async addToCart() {
            let data = {
                product_sku: this.config.sku,
                product_price: this.config.price,
                product_quantity: this.config.qty,
                cart_options: [],
                product_sku_option: this.get_product_sku()
            },
            is_pass = true;
            var process_data =  this.processAddToCart(this.config.options.RECTANGLE, data, is_pass);
            data = process_data.data;
            is_pass = process_data.is_pass;
            process_data = this.processAddToCart(this.config.options.RADIO, data, is_pass);
            data = process_data.data;
            is_pass = process_data.is_pass;

            if (is_pass) {
                let response = await fetch('/api/cart-items/',
                    {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': this.config.csrf_token,
                        },
                        body: JSON.stringify(data)
                    }
                );
                if (response.ok) {
                    this.updateMinicart(this);
                    let modal_el = document.getElementById("preview-cart-modal");
                    this.modal = new bootstrap.Modal(modal_el);
                    this.modal.show()
                }
            }
        },

        convertPrice(price) {
            return price.toFixed(2).replace(/(\d)(?=(\d{3})+\.)/g, '$1,');
        },

        updateMinicart($this) {
            let self = $this;
            $.ajax({
                url: "/api/cart/",
                method: "GET",
            }).done(function (data) {
                data.gst = self.convertPrice(data.gst);
                data.subtotal = self.convertPrice(data.subtotal);
                data.total = self.convertPrice(data.total);
                data.shipping = self.convertPrice(data.shipping);

                let event = new CustomEvent("update-mini-cart", {
                    detail: {
                        cart: {
                            cart_count: data.count,
                            subtotal: data.subtotal
                        }
                    }
                });
                self.data_cart = data
                window.dispatchEvent(event);
            });
        },
        countClick(e) {
            if (e) {
                this.clickCount++;
            }
            if (e && this.clickCount % 2 === 0 || this.clickCount !== 0) {
                this.modal.hide();
            }
        },
        get_item_price(item) {
            let price = "$" + item.min_price;
            if (parseFloat(item.max_price) > parseFloat(item.min_price)) {
                price += " - $" + item.max_price;
            }
            return price;
        },
        replaceImage: function (thumbSrc) {
            // Set the src attribute of the main image element to the clicked thumbnail src
            if (thumbSrc) {
                if (document.querySelector('.main')) {
                    document.querySelector('.main').src = thumbSrc;
                }
            } else {
                return ''
            }
        },
        // clickThumbImage: function (e) {
        //     let slider = document.querySelector('.product-slider');
        //     let thumbs = slider.querySelectorAll('.slick-slide img');
        //     let arrThumbs = Array.from(thumbs);
        //     let thumbSrc = e.target.dataset.src;
        //     // Remove class for all other item
        //     for (let thumb of arrThumbs) {
        //         thumb.classList.remove('show-img');
        //     }
        //
        //     // Add class for item active
        //     e.target.classList.add('show-img');
        //
        //     // Set the src attribute of the main image element to the clicked thumbnail src
        //     this.replaceImage(thumbSrc);
        // }
    },
    beforeCreate() {
        this.loading = true;
    },
    updated() {
        this.changeImage()
        this.loading = false;
    },
    mounted() {
        this.default_price = this.config.price;
        this.reUpdateOption();
        this.reCalculatePrice();
        this.items = this.config.relate_items;
    }
})
