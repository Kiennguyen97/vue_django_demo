var app = new Vue({
    el: "#vue-app",
    data: {
        config: context,
        items: {
            "store_lists": [],
            "resellers": [],
        },
        selected: {},
        resellers_toggle: false,
    },
    methods: {
        async selectedRegion(event){
            let self = this;
            let id = event.target.value;
            this.config.items.forEach(function(item, index){
                if(item.uuid == id){
                    self.selected = item;
                }
            })
            await this.get_store_location(id);
        },
        async get_store_location(id){
            let self = this,
                api_url = this.config.url_key,
                data = {};
            try {
                data["region_uuid"] = id;
                let response = await fetch(api_url,
                    {
                        method: 'POST',
                        headers: {
                          'Content-Type': 'application/json',
                          'X-CSRFToken': self.config.csrf_token,
                        },
                        body: JSON.stringify(data)
                    }
                );
                let res = await response.json();
                this.items = res;
            }catch (err) {
                console.log(err)
            }
        }
    },
    mounted() {
    }
})