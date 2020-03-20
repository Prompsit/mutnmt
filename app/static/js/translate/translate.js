$(document).ready(function() {
    $('.engine-select').on('change', function() {
        $('.translate-form').attr('data-status', 'false');
    });

    let onclick = (e) => {
        if ($('.translate-form').attr('data-status') == 'ready') {
            $.ajax({
                url: `get`,
                method: "POST",
                data: {
                    text: $('.translate-text').val()
                }
            }).done(function(raw) {
                $('.translation-target-text').html(raw);
            });
        } else {
            $('.translate-form').attr('data-status', 'launching');

            $.ajax({
                url: `attach_engine/${$('.engine-select option:selected').val()}`
            }).done(function(raw) {
                console.log(raw);
                if (raw == "0") {
                    $('.translate-form').attr('data-status', 'ready');
                    onclick()
                } else {
                    $('.translate-form').attr('data-status', 'error');
                }
            });
        }

        return false;
    }

    $('.translate-form .translate-btn').on('click', function() {
        return onclick()
    });
});

$(window).on('unload', function() {
    if (navigator.sendBeacon) {
        navigator.sendBeacon('leave');
    } else {
        $.ajax({ url: `leave`, async: false, type: "post" });
    }
})