$(document).ready(function() {
    $("[data-toggle=hamburger]").on('click', function() {
        $(`${$(this).attr("data-target")}`).toggleClass("show");
        $('body').toggleClass("overflow-hidden")
    });

    $(".nile-resurrect-btn").on('click', function(e) {
        e.preventDefault();
        $('.tour-guide').removeClass('hidden');
    });
});