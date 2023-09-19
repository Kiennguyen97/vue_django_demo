var app = new Vue({
    el: "#vue-app",
    data: {
        config: context,
        items: [],
        news: [],
        childs: [],
        pagination: [],
        sort_options: {},
        page_number: 1,
        request_data: {},
        count_product: 0,
        is_search: context.is_search,
        search_header: '',
        is_featured: '',
        is_free_shipping: '',
        search_from_sub_category: true,
        price_from: '',
        price_to: '',
        show_products: true,
        show_advance_search: false,
        sort_options_news: {},
        is_show_empty_alert:false,
        loading: false,
    },
    methods: {
        async load(first = false){
            this.loading = true;
            try {

                let self = this,
                    api_url = "/api/product/reload";
                this.request_data["page_number"] = this.page_number;
                this.request_data["number_item"] = this.config.number_item;
                this.request_data["uuid"] = this.config.uuid;
                this.request_data["first"] = first;
                this.request_data["ordering"] = this.sort_options.default_value;
                this.request_data["ordering_news"] = this.sort_options_news.default_value;
                this.request_data["is_search"] = this.is_search;
                // if (this.is_search) {
                //     this.request_data["advance_search"] = {
                //         is_featured: this.is_featured,
                //         is_free_shipping: this.is_free_shipping,
                //         price_from: this.price_from,
                //         price_to: this.price_to,
                //         search_from_sub_category: this.search_from_sub_category,
                //     }
                // }
                let response = await fetch(api_url,
                    {
                        method: 'POST',
                        headers: {
                          'Content-Type': 'application/json',
                          'X-CSRFToken': self.config.csrf_token,
                          'Class-Name': self.config.page_type
                        },
                        body: JSON.stringify(this.request_data)
                    }
                );
                let res = await response.json();
                this.loading = false;
                if (res["items"]){
                    self.items = res["items"];
                    if(self.items.length < 1){
                        this.is_show_empty_alert = true;
                    }
                    if(self.items.length === 1){
                        self.resultFound = self.items.length;
                    }
                }
                if (res["news"]){
                    self.news = res["news"];
                }
                if (self.is_search){
                    self.count_product = res["items"].length;
                    self.search_header = self.count_product > 1 ? self.count_product + " results for '" + self.config.uuid + "'"
                        : self.count_product + " result for '" + self.config.uuid + "'";
                }
                if (res["childs"]){
                    self.childs = res["childs"];
                }
                if (res["pagination"]){
                    self.pagination = res["pagination"];
                }
            }catch (err) {
                this.loading = false;
            }
        },
        async sortBy(event){
            this.load()
        },

        convertPrice(price) {
            return price.toFixed(2).replace(/(\d)(?=(\d{3})+(?!\d))/g, '$1,');
        },

        get_item_price(item){
            let price = "$" + this.convertPrice(item.min_price);
            if(!item.can_purchase){
                price = "POA";
            }else{
                if (parseInt(item.number_total) > 0){
                    price = "From $" + this.convertPrice(item.min_price);
                }
            }
            return price;
        },

        showProducts(){
            this.show_products = true;
            this.show_news = false;
        },


        // showAdvanceSearch() {
        //     this.show_advance_search = !this.show_advance_search;
        // },

        async sortByNews(event){
            this.load()
        },

        reloadImage: function() {
            // class card-image.lazyloaded
            document.querySelectorAll('.card-image.lazyloaded').forEach(function(img){
                img.setAttribute('src', img.getAttribute('data-src'));
            });
        },

        // advanceSearch() {
        //     let form = document.forms["advanced-search-form"];
        //     // Then submit if form is OK.
        //     if (this.price_from && this.price_to) {
        //         if (parseFloat(this.price_to) < parseFloat(this.price_from)) {
        //             // add validation error to price to
        //             form["price_to"].setCustomValidity("Price to must be larger than price from "
        //                 + this.price_from + ". Please enter a valid price.");
        //             form["price_to"].reportValidity();
        //         }else {
        //             form["price_to"].setCustomValidity("");
        //         }
        //     }
        //     var reportValidity = form.reportValidity();
        //     if (reportValidity) {
        //         this.load();
        //     }
        // }
        selectePage(i){
            this.page_number = i;
            this.load()
        }
    },
    created(){
        this.is_show_empty_alert = false;
    },
    mounted() {
        this.sort_options = {
            default_value: this.config.sort_options[0].value,
            options: this.config.sort_options
        }
        this.sort_options_news = {
            default_value: this.config.sort_options_news[0].value,
            options: this.config.sort_options_news
        }
        this.load(true);
    },
    updated(){
        this.reloadImage();
    }
})