$(document).ready(function() {
    $('.engine-select').on('change', function() {
        $('.translate-form').attr('data-status', 'false');
    });

    let onsubmit = (e) => {
        $(".inspect-compare-content").addClass("d-none");

        $('.user-engine-target').html("");
        $('.engine-target').html("");

        let text = $('.translate-text').val();

        if ($('.translate-form').attr('data-status') == 'ready') {
            $.ajax({
                url: `get`,
                data: { "text": text},
                method: "post"
            }).done(function(inspection) {
                let translation = inspection['postproc']
                $('.user-engine-target').html(translation);
                $('.google-link').attr('href', `https://translate.google.com/#view=home&op=translate&sl=${inspection['source']}&tl=${inspection['target']}&text=${text}`)
                $('.deepl-link').attr('href', `https://www.deepl.com/translator#${inspection['source']}/${inspection['target']}/${text}`)
                $(".inspect-compare-content").removeClass("d-none");
            });
        } else {
            $('.translate-form').attr('data-status', 'launching');

            $.ajax({
                url: `attach_engine/${$('.engine-select option:selected').val()}`
            }).done(function(raw) {
                console.log(raw);
                if (raw == "0") {
                    $('.translate-form').attr('data-status', 'ready');
                    onsubmit()
                } else {
                    $('.translate-form').attr('data-status', 'error');
                }
            });
        }

        return false;
    }

    $('.translate-form').on('submit', function() {
        return onsubmit()
    });
});

$(window).on('unload', function() {
    if (navigator.sendBeacon) {
        navigator.sendBeacon('leave');
    } else {
        $.ajax({ url: `leave`, async: false, type: "post" });
    }
})