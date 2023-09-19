$(function () {

    //=============================== Quick Search =================================//

    const contentSearch = document.querySelector('.dropdown-quicksearch');
    const buttonSearch = document.querySelector('.dropdown-quicksearch-icon');

    document.addEventListener('mouseup', function (e) {
        if (buttonSearch.contains(e.target) === false && contentSearch.contains(e.target) === false && contentSearch.classList.contains('is-open')) {
            contentSearch.classList.remove('is-open');
            contentSearch.setAttribute("aria-hidden", true);
        }
    });
    buttonSearch.addEventListener("click", function () {
        if (contentSearch.classList.contains('is-open')) {
            contentSearch.classList.remove('is-open');
            contentSearch.setAttribute("aria-hidden", true);
        } else {
            contentSearch.classList.add('is-open');
            contentSearch.setAttribute("aria-hidden", false);
            contentSearch.querySelector('#rp-input-search').focus();
        }
    });

    //=============================== Mega Menu =================================//

    // Hide and show the main menu on mobile
    const contentMenu = document.querySelector('.nav-pages-container');
    const buttonMenu = document.querySelector('.mobile-menu-toggle');

    document.addEventListener('mouseup', function (e) {
        if (buttonMenu.contains(e.target) === false && contentMenu.contains(e.target) === false && contentMenu.classList.contains('is-open')) {
            document.body.classList.remove('active-menu');
            contentMenu.classList.remove('is-open');
            contentMenu.setAttribute("aria-hidden", true);
        }
    });

    function toggleMenu() {
        const menu = document.getElementById('menu');

        // If it's open, close it; if it's closed, open it
        if (menu.classList.contains('is-open')) {
            document.body.classList.remove('active-menu');
            menu.classList.remove('is-open');
            menu.setAttribute('aria-hidden', true);
        } else {
            document.body.classList.add('active-menu');
            menu.classList.add('is-open');
            menu.setAttribute('aria-hidden', false);
        }
    }

    // Hide the main menu mobile when resize to desktop screen
    function hideMenuMobile() {
        const menu = document.getElementById('menu');

        // If it's open, close it; if it's closed, open it
        if (menu.classList.contains('is-open') && window.innerWidth > 800) {
            document.body.classList.remove('active-menu');
            menu.classList.remove('is-open');
            menuToggle.nextElementSibling.setAttribute('aria-hidden', true);
        }
    }

    window.addEventListener('resize', hideMenuMobile);

    // Get the dropdown toggle from the dropdown
    const getDropdownToggle = dropdown => dropdown.querySelector('.has-submenu');

    // Open the dropdown
    function openDropdown(dropdown) {
        const dropdownToggle = getDropdownToggle(dropdown);

        // There is no sibling selector, so we jump to the parent and do a query
        const siblingDropdowns = dropdown.parentNode.querySelectorAll('.nav-pages-list > .nav-pages-item.is-open');

        // First we'll close the other open dropdowns
        [...siblingDropdowns].forEach((dropdown) => closeDropdown(dropdown, false));

        // Finally, set aria-expanded to true and add the open class
        dropdownToggle.setAttribute('aria-expanded', true);
        dropdownToggle.nextElementSibling.setAttribute('aria-hidden', false);
        dropdown.classList.add('is-open');
    }

    // Close the dropdown
    function closeDropdown(dropdown, moveFocus = true) {
        const dropdownToggle = getDropdownToggle(dropdown);

        // Set aria-expanded to false and remove the open class
        dropdownToggle.setAttribute('aria-expanded', false);
        dropdownToggle.nextElementSibling.setAttribute('aria-hidden', true);
        dropdown.classList.remove('is-open');

        // Move the focus back to the toggle if we're allowed to
        if (moveFocus) {
            dropdownToggle.focus();
        }
    }

    // Close it if it's open or open it if it's closed
    function toggleDropdown(event) {
        event.stopPropagation();
        let dropdown = '';
        let elementAction = this.parentNode;
        if (elementAction.classList.contains('nav-pages-action')) {
            dropdown = elementAction.parentNode;
            event.preventDefault();
        } else {
            dropdown = this.parentNode;
        }
        if (dropdown) {
            if (dropdown.classList.contains('is-open')) {
                closeDropdown(dropdown);
            } else {
                openDropdown(dropdown);
            }
        }
    }

    // Hide dropdowns megamenu
    function hideDropdowns(event) {
        const menu = document.getElementById('menu');

        // If the user clicked anywhere or hit the escape key
        if (event.type === 'click' && menu.contains(event.target) === false) {
            const openDropdowns = document.querySelectorAll('.nav-pages-item.is-open');

            // Close all the dropdowns (but don't move focus if the event was a click)
            [...openDropdowns].forEach((dropdown) => closeDropdown(dropdown, event.type !== 'click'));
        }
    }

    // Ready set navigate
    function readySetNavigate() {
        const menuToggle = document.getElementById('mobile-menu-toggle');
        let dropdownToggles = '';
        if (window.innerWidth < 801) {
            dropdownToggles = document.querySelectorAll('.nav-pages-action-icon');
        } else {
            dropdownToggles = document.querySelectorAll('.has-submenu');
        }

        // add the click listener for the main menu toggle
        menuToggle.addEventListener('click', toggleMenu);

        // add the click listener for all of the dropdown toggles
        [...dropdownToggles].forEach((dropdownToggle) => {
            dropdownToggle.addEventListener('click', toggleDropdown);
        });

        // add the click listener to close the dropdowns
        document.addEventListener('click', hideDropdowns);
    }

    readySetNavigate();
    window.addEventListener('resize', readySetNavigate);

    //=============================== Accordion Faqs =================================//

    // Get all FAQ items and add click event listener
    const faqItems = document.querySelectorAll('.shogun-accordion');
    faqItems.forEach(function (item) {
        item.querySelector('.shogun-accordion-body').style.visibility = 'hidden';
        item.addEventListener('click', () => {

            // Get the FAQ item content element
            const content = item.querySelector('.shogun-accordion-body');

            // Hide all items except for the clicked item
            faqItems.forEach(function (accItem) {
                if (accItem !== item) {
                    accItem.classList.remove('shogun-accordion-active');
                    accItem.querySelector('.shogun-accordion-body').style.visibility = 'hidden';
                    accItem.querySelector('.shogun-accordion-body').style.maxHeight = null;
                }
            });

            // Toggle the active class on the clicked FAQ item
            item.classList.toggle('shogun-accordion-active');

            // Toggle the max-height property to expand/collapse the content
            content.style.maxHeight = content.style.maxHeight ? null : content.scrollHeight + 'px';
            setTimeout(function () {
                content.style.visibility = content.style.visibility === 'hidden' ? 'visible' : 'hidden';
            }, 200);
        });
    });

    //=============================== Popup Checkout =================================//

    // Get url params
    function getAllUrlParams(url) {
        var queryString = url ? url.split('?')[1] : window.location.search.slice(1);
        var obj = {};
        if (queryString) {
            queryString = queryString.split('#')[0];
            var arr = queryString.split('&');

            for (var i = 0; i < arr.length; i++) {
                var a = arr[i].split('=');
                var paramName = a[0];
                var paramValue = typeof (a[1]) === 'undefined' ? true : a[1];

                paramName = paramName.toLowerCase();
                if (typeof paramValue === 'string') paramValue = paramValue.toLowerCase();

                if (paramName.match(/\[(\d+)?\]$/)) {
                    var key = paramName.replace(/\[(\d+)?\]/, '');
                    if (!obj[key]) obj[key] = [];

                    if (paramName.match(/\[\d+\]$/)) {
                        var index = /\[(\d+)\]/.exec(paramName)[1];
                        obj[key][index] = paramValue;
                    } else {
                        obj[key].push(paramValue);
                    }
                } else {
                    if (!obj[paramName]) {
                        obj[paramName] = paramValue;
                    } else if (obj[paramName] && typeof obj[paramName] === 'string') {
                        obj[paramName] = [obj[paramName]];
                        obj[paramName].push(paramValue);
                    } else {
                        obj[paramName].push(paramValue);
                    }
                }
            }
        }

        return obj;
    }

    // Show popup checkout
    function showPopupCheckout() {
        let buttonCheckout = document.querySelector('.cart-actions-top .checkout-show');
        if (buttonCheckout) {
            let url = window.location.href;
            var params = getAllUrlParams(url);
            if (params.action === 'checkout') {
                buttonCheckout.click();
            }
        }
    }

    showPopupCheckout();

    //=============================== Animation When Scrolling Through Area =================================//
    function animationElement() {
        // Get element
        const elDom = document.querySelector('.laundry-content .banner-image .bt-image');
        // Attach a scroll event listener to the window
        window.addEventListener('scroll', function () {
            // Get position of the element
            if (elDom) {
                const rectEl = elDom.getBoundingClientRect();

                // Check if scrolling down or up
                if (rectEl.top < window.innerHeight && rectEl.bottom >= 0) {
                    // Element visible in the browser window
                    if (!elDom.classList.contains('animate__animated')) {
                        elDom.style.display = 'block';
                        elDom.classList.add('animate__animated', 'animate__fadeInDown', 'animate__delay-1s');
                    }
                } else {
                    // Element not visible in browser window
                    elDom.style.display = 'none';
                    elDom.classList.remove('animate__animated', 'animate__fadeInDown', 'animate__delay-1s');
                }
            }
        });
    }

    animationElement();

    //=============================== Animation Hide/show Header =================================//
    var isUserScrolled = false;

    function hideShowHeader() {
        const elementScroll = document.getElementById('header-container');

        // Get the height of the element
        const headerHeight = elementScroll.offsetHeight;

        // Get the last position
        let lastScrollPosition = window.scrollY;

        // Add padding body
        document.body.style.cssText = `padding-top: ${headerHeight}px`;

        if (isUserScrolled) {
            // Attach a scroll event listener to the window
            window.addEventListener("scroll", function () {

                // Get the current position
                let currentScrollPosition = window.scrollY;

                // Hide/show header
                if (currentScrollPosition > lastScrollPosition && currentScrollPosition > headerHeight) {
                    elementScroll.classList.add('hider');
                    elementScroll.style.cssText = `top:-${headerHeight + 5}px`;
                } else {
                    elementScroll.classList.remove('hider');
                    elementScroll.style.top = 0;
                }

                lastScrollPosition = currentScrollPosition;
            });
        }
    }

    hideShowHeader();
    window.addEventListener('resize', hideShowHeader);

    // Set isUserScrolled is true
    window.addEventListener("wheel", function () {
        isUserScrolled = true;
        hideShowHeader();
    }, {once: true});

    window.addEventListener("touchstart", function () {
        isUserScrolled = true;
        hideShowHeader();
    }, {once: true});

    window.addEventListener("keydown", function () {
        isUserScrolled = true;
        hideShowHeader();
    }, {once: true});


    //=============================== Custom upload input upload file ===============================//

    function uploadFile(idInputFile) {
        const inputFile = document.getElementById(idInputFile);
        const infoArea = document.querySelector('.upload-file-name');

        // Listener on change event
        if (inputFile) {
            inputFile.addEventListener('change', function (e){

                // Get DOM element when listener on change event
                const eTarget = e.target;

                // Show file name
                if (infoArea){
                    infoArea.textContent = eTarget.files[0].name;
                }
            });
        }
    }

    uploadFile('id_proof_purchase');

    //=============================== Custom Select Box ===============================//

    function customSelect(){
        var x, i, j, l, ll, selElmnt, a, b, c;
        /* Look for any elements with the class "custom-select": */
        x = document.getElementsByClassName("custom-select-option");
        l = x.length;
        for (i = 0; i < l; i++) {
            selElmnt = x[i].getElementsByTagName("select")[0];
            ll = selElmnt.length;
            /* For each element, create a new DIV that will act as the selected item: */
            a = document.createElement("DIV");
            a.setAttribute("class", "select-selected");
            a.innerHTML = selElmnt.options[selElmnt.selectedIndex].innerHTML;
            x[i].appendChild(a);
            /* For each element, create a new DIV that will contain the option list: */
            b = document.createElement("DIV");
            b.setAttribute("class", "select-items select-hide");
            for (j = 1; j < ll; j++) {
                /* For each option in the original select element,
                create a new DIV that will act as an option item: */
                c = document.createElement("DIV");
                c.innerHTML = selElmnt.options[j].innerHTML;
                c.addEventListener("click", function(e) {
                    /* When an item is clicked, update the original select box,
                    and the selected item: */
                    var y, i, k, s, h, sl, yl;
                    s = this.parentNode.parentNode.getElementsByTagName("select")[0];
                    sl = s.length;
                    h = this.parentNode.previousSibling;
                    for (i = 0; i < sl; i++) {
                        if (s.options[i].innerHTML == this.innerHTML) {
                            s.selectedIndex = i;
                            h.innerHTML = this.innerHTML;
                            y = this.parentNode.getElementsByClassName("same-as-selected");
                            yl = y.length;
                            for (k = 0; k < yl; k++) {
                                y[k].removeAttribute("class");
                            }
                            this.setAttribute("class", "same-as-selected");
                            break;
                        }
                    }
                    h.click();
                });
                b.appendChild(c);
            }
            x[i].appendChild(b);
            a.addEventListener("click", function(e) {
                /* When the select box is clicked, close any other select boxes,
                and open/close the current select box: */
                e.stopPropagation();
                closeAllSelect(this);
                this.nextSibling.classList.toggle("select-hide");
                this.classList.toggle("select-arrow-active");
            });
        }
    }

    function closeAllSelect(elmnt) {
        /* A function that will close all select boxes in the document,
        except the current select box: */
        var x, y, i, xl, yl, arrNo = [];
        x = document.getElementsByClassName("select-items");
        y = document.getElementsByClassName("select-selected");
        xl = x.length;
        yl = y.length;
        for (i = 0; i < yl; i++) {
            if (elmnt == y[i]) {
                arrNo.push(i)
            } else {
                y[i].classList.remove("select-arrow-active");
            }
        }
        for (i = 0; i < xl; i++) {
            if (arrNo.indexOf(i)) {
                x[i].classList.add("select-hide");
            }
        }
    }

    /* If the user clicks anywhere outside the select box,
    then close all select boxes: */
    document.addEventListener("click", closeAllSelect);

    // Call function
    customSelect()
});
