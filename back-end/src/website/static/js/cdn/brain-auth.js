var button=document.querySelector("#submit-button");const form=document.getElementById("brain-form");braintree.dropin.create({authorization:document.getElementById("submit-button").dataset.clienttoken,container:"#dropin-container"},function(t,e){button.addEventListener("click",function(t){"c_d_card"==document.getElementById("payment-type").value&&(t.preventDefault(),e.requestPaymentMethod(function(t,e){t?console.log("Error",t):(document.querySelector("#nonce").value=e.nonce,form.submit())}))})});