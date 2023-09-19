var app = new Vue({
    el: "#checkout-cart",
    data: {
        config: context,
        modal: "",
        items: [],
        merchant_lists: {},
        region_lists: {
            default: 'all',
            lists: [],
        },
        selected_merchant: {
            selected: false,
            data: {}
        },
        placed_order: false,
        steps: [
            {'name': 'Your Details', 'active': true, 'complete': false, 'next_comma': ' » ', 'code': 'your_details'},
            {'name': 'Pickup Location', 'active': false, 'complete': false, 'next_comma': ' » ', 'code': 'pickup_location'},
            {'name': 'Payment', 'active': false, 'complete': false, 'next_comma': ' » ', 'code': 'payment'},
            {'name': 'Confirmation', 'active': false, 'complete': false, 'next_comma': ' » ', 'code': 'confirmation'},
            {'name': 'Thanks', 'active': false, 'complete': false, 'next_comma': ' ', 'code': 'thanks'},
        ],
        your_details: {
            'name': '',
            'phone': '',
            'email': '',
            'customer_id': '',
        },
        billing_address: {
            'billing_name': '',
            'billing_addr1': '',
            'billing_addr2': '',
            'billing_town': '',
            'billing_postcode': '',
        },
        payment_methods: [],
        selectedPayment: 'd_d',
        payment_method_nonce: '',
        credit_card_number: '',
        order_code: '',
        error_message: false,
        show_error: false,
        g_recaptcha_response: '',
    },
    methods: {
        nextStep(e, action = 'next') {
            let active_step = this.steps.findIndex(step => step.active == true);
            if (this.steps[active_step].code == 'your_details') {
                let form = document.forms['your_details_form'];
                var reportValidity = form.reportValidity();
                if (reportValidity) {
                    let your_details = {
                        'name': this.your_details.name,
                        'phone': this.your_details.phone,
                        'email': this.your_details.email,
                    }
                    let billing_address = {
                        'billing_name': this.billing_address.billing_name,
                        'billing_addr1': this.billing_address.billing_addr1,
                        'billing_addr2': this.billing_address.billing_addr2,
                        'billing_town': this.billing_address.billing_town,
                        'billing_postcode': this.billing_address.billing_postcode,
                    }
                    sessionStorage.setItem('your_details', JSON.stringify(your_details));
                    sessionStorage.setItem('billing_address', JSON.stringify(billing_address));
                } else {
                    return false;
                }
            } else if (this.steps[active_step].code == 'pickup_location') {
                if (!this.selected_merchant.selected && action == 'next') {
                    this.show_error = true;
                    return false;
                }
                this.show_error = false;
                let selected_merchant = this.selected_merchant;
                sessionStorage.setItem('selected_merchant', JSON.stringify(selected_merchant));
            }

            if (action == 'next') {
                if (this.steps[active_step].code == 'thanks') {
                    this.backHome();
                    return false;
                }
                this.steps[active_step].active = false;
                this.steps[active_step].complete = true;
                this.steps[active_step + 1].active = true;
            } else if (action == 'prev') {
                this.steps[active_step].active = false;
                this.steps[active_step - 1].active = true;
                this.steps[active_step - 1].complete = false;
            }
        },

        chooseMerchant(item) {
            this.selected_merchant.data = item;
            this.selected_merchant.selected = true;
        },

        userRecaptcha() {
            let self = this;
            grecaptcha.ready(function() {
                grecaptcha.execute(self.config.site_key, {action: 'submit'}).then(function (token) {
                    // self.nextStep();
                    // verify the token on the server side.
                    self.g_recaptcha_response = token;
                    let method = 'POST';
                    let url = '/site_verify/';
                    let headers = {
                        'X-CSRFToken': self.config.csrf_token,
                        'Content-Type': 'application/json',
                    }
                    let body = JSON.stringify({'token': token});
                    fetch(url, {
                        method: method,
                        headers: headers,
                        body: body,
                    }).then(response => response.json())
                        .then(data => {
                            if (data.status == 'success') {
                                self.nextStep();
                            }
                        });
                });
            });
        },

        placeOrder() {
            let self = this;
            grecaptcha.ready(function() {
                grecaptcha.execute(self.config.site_key, {action: 'submit'}).then(function (token) {
                    
                    let data = {
                        'g-recaptcha-response': token,
                        'your_details': self.your_details,
                        'address-bill': self.billing_address,
                        'address_merchant': self.selected_merchant.data.uuid,
                        'payment-type': self.selectedPayment,
                        payment_method_nonce: self.payment_method_nonce,
                    }

                    let url = self.config.place_order_url;
                    let method = 'POST';
                    let headers = {
                        'X-CSRFToken': self.config.csrf_token,
                        'Content-Type': 'application/json',
                    }
                    let body = JSON.stringify(data);

                    fetch(url, {
                        method: method,
                        headers: headers,
                        body: body,
                    }).then(response => response.json())
                    .then(data => {
                        if (data.status == 'success') {
                            self.order_code = data.order_code;
                            self.error_message = false;
                            self.nextStep();
                            self.clearSessionStorage();
                        } else {
                            self.your_details.customer_id = data.customer_id;
                            self.placed_order = false;
                            self.error_message = data.message;
                        }
                    })
                })
            })
            
        },

        backHome() {
            window.location.href = '/';
        },

        initBraintree() {
            const button = document.querySelector("#place-order");
            const self = this;
            braintree.dropin.create(
                {
                    authorization: this.config.client_token,
                    container: "#dropin-container",
                },
                function (t, e) {
                    button.addEventListener("click", function (t) {
                        self.placed_order = true;
                        if ("c_d_card" === self.selectedPayment) {
                            t.preventDefault();
                            e.requestPaymentMethod(function (t, e) {
                                if (t) {
                                    console.log("Error", t);
                                    self.placed_order = false;
                                }else {
                                    self.payment_method_nonce = e.nonce;
                                    self.credit_card_number = "**** **** **** " + e.details.lastFour;
                                    self.placeOrder();
                                }
                            });
                        } else {
                            self.placeOrder();
                        }
                    });
                }
            );
        },
        clearSessionStorage() {
            sessionStorage.removeItem('your_details');
            sessionStorage.removeItem('billing_address');
            sessionStorage.removeItem('selected_merchant');
            sessionStorage.removeItem('config');
        }
    },
    mounted() {
        let config = sessionStorage.getItem('config');
        if ((this.config && !config) || (this.config && this.config.is_get_view)) {
            sessionStorage.setItem('config', JSON.stringify(this.config));
        }
        this.config = config ? JSON.parse(config) : this.config;
        this.merchant_lists = this.config.merchant_lists;
        this.region_lists = {
            default: this.config.region_lists[0].code,
            lists: this.config.region_lists
        }
        this.payment_methods = this.config.payment_methods;

        // get data from session storage
        let your_details = sessionStorage.getItem('your_details');
        let billing_address = sessionStorage.getItem('billing_address');
        let selected_merchant = sessionStorage.getItem('selected_merchant');

        this.your_details = your_details ? JSON.parse(your_details) : this.your_details;
        this.billing_address = billing_address ? JSON.parse(billing_address) : this.billing_address;
        this.selected_merchant = selected_merchant ? JSON.parse(selected_merchant) : this.selected_merchant;
        const script = document.createElement('script');
        script.setAttribute('src', 'https://js.braintreegateway.com/web/dropin/1.32.0/js/dropin.js');
        script.onload = () => {
            this.initBraintree();
        };
        document.head.appendChild(script);
    }
})