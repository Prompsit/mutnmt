let force_quit = false;

$(document).ready(function() {
    let file_source = null;
    let file_target = null;
    let bitext_file = null;

    let drag_callback = (e, file) => {
        if ($(e).hasClass("source_file")) {
            file_source = file
        } else if ($(e).hasClass("target_file")) {
            file_target = file
        } else {
            bitext_file = file
        }
    }

    FileDnD(".source_file", function(file) {
        drag_callback($(".source_file"), file)
    });

    FileDnD(".target_file", function(file) {
        drag_callback($(".target_file"), file)
    });

    FileDnD(".bitext_file", function(file) {
        drag_callback($(".bitext_file"), file)
    });

    $('.text-col, .bitext-col').on('mouseenter', function() {
        let other = $('.text-col, .bitext-col').not(this);
        $(other).addClass('target-col-disabled')
    });

    $('.text-col, .bitext-col').on('mouseleave', function() {
        let other = $('.text-col, .bitext-col').not(this);
        $(other).removeClass('target-col-disabled')
    });

    $(".bitext_file").on('click', function() {
        file_source = null;
        file_target = null;
        $(".source_file, .target_file").removeClass("dragged");
    })

    $(".monolingual-nav-tab").on('click', function(e) {
        e.preventDefault();
        if ($(this).closest("fieldset").prop("disabled") == true) return;

        $(".target-file-col, .target-lang-col, .bitext-col").addClass("target-col-disabled");
        $(".target_file").removeClass("dragged");
        $(".upload-nav-tabs .nav-link").removeClass("active");
        $(this).addClass("active");
        file_target = null;
    });

    $(".bilingual-nav-tab").on('click', function(e) {
        e.preventDefault();
        $(".target-file-col, .target-lang-col, .bitext-col").removeClass("target-col-disabled");
        $(".upload-nav-tabs .nav-link").removeClass("active");
        $(this).addClass("active");
    });

    $(".data-upload-form").on("submit", function(e) {
        e.preventDefault();

        $(".data-upload-form fieldset").prop("disabled", true);

        $(".token-alert").addClass("d-none");

        if (file_source == null && bitext_file == null) return false;

        $('.translate-form').attr('data-status', 'launching');

        let data = new FormData();
        data.append("name", $("#name").val());
        data.append("description", $("#description").val());
        data.append("source_lang", $(".source_lang option:selected").val());
        data.append("target_lang", $(".target_lang option:selected").val());

        if (bitext_file) {
            data.append("bitext_file", bitext_file)
        } else {
            data.append("source_file", file_source)
            if (file_target) data.append("target_file", file_target)
        }

        $(".token-alert").removeClass("d-none");

        $.ajax({
            url: $(this).attr("action"),
            method: 'POST',
            data: data,
            contentType: false,
            cache: false,
            processData: false,
            xhr: function() {
                let xhr = new window.XMLHttpRequest();
                xhr.upload.addEventListener('progress', function(e) {
                    if (e.lengthComputable) {
                        $(".upload-progress-container").removeClass("d-none");
                        let prozent = parseInt((e.loaded / e.total) * 100);
                        $(".upload-progress").html(prozent);
                    }
                }, false);
                return xhr;
            },
            success: function(data) {
                force_quit = true;
                if (data.result == 200) {
                    longpoll(3000, {
                        url: '/data/upload_status',
                        method: 'post',
                        data: { task_id: data.task_id }
                    }, function(data) {
                        if (data.result == 200) {
                            window.location.href = window.location.href;
                        } else if (data.result == -2) {
                            window.location.href = window.location.href;
                        }
                    });
                } else {
                    window.location.href = window.location.href;
                }
            }
        });

        return false;
    });
});

$(window).on('beforeunload', () => {
    let filled = false;
    $(".data-upload-form input:not(.btn), .data-upload-form textarea").each(function(i, el) {
        filled = filled || $(el).val() != "";
        if (filled) console.log(el);
    });

    if (filled && !force_quit) return true;
})