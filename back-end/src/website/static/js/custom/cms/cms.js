$(function () {

    // Accordion FAQS
    $(document).ready(function () {
        $(".shogun-accordion-heading").on('click',function(){
            if($(this).parent().hasClass('shogun-accordion-active')){
                $(this).parent().removeClass('shogun-accordion-active').find(".shogun-accordion-body").slideUp('fast').animate({
                    opacity: 0
                }, 500);
            }else{
                $(this).parent().addClass('shogun-accordion-active').find(".shogun-accordion-body").slideDown('fast').animate({
                    opacity: 1
                }, 500);
            }
            $(this).parent().prevAll().removeClass('shogun-accordion-active').find(".shogun-accordion-body").slideUp('fast').css('opacity', 0);
            $(this).parent().nextAll().removeClass('shogun-accordion-active').find(".shogun-accordion-body").slideUp('fast').css('opacity', 0);
        });
    });
});