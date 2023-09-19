var app = new Vue({
    el: "#universal",
    data: {
        config: '',
        form: "",
        g_recaptcha_response: '',
    },
    methods: {
        onSubmitUniversal() {
            this.form = document.getElementById('universal-form');
            let site_key = this.form.getAttribute('data-site-key');
            let reportValidity = this.form.reportValidity();
            if (reportValidity) {
              this.userRecaptcha(site_key);
            }
        },

        userRecaptcha(site_key) {
            let self = this;
            let recaptcha_site_key = site_key;
            grecaptcha.ready(function () {
                grecaptcha.execute(recaptcha_site_key, {action: 'submit'}).then(function (token) {
                    self.form.querySelector('textarea[name="g-recaptcha-response"]').value = token;
                    // verify the token on the server side.
                    self.form.submit();
                });
            });
        },
    },
    mounted() {

    }
})