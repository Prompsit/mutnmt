let force_quit = false;

$(document).ready(function() {
    let file_source = null;
    let file_target = null;
    let bitext_file = null;

    let drag_callback = (e, file) => {
        console.log('callback', e, file);
        if ($(e).hasClass("source_file")) {
            file_source = file
        } else if ($(e).hasClass("target_file")) {
            file_target = file
        } else {
            bitext_file = file
        }
    }

    FileDnD(".source_file", function(file) {
        bitext_file = null;
        $(".bitext_file").removeClass("dragged");
        $(".bitext_file input").val('');

        drag_callback($(".source_file"), file)
    });

    FileDnD(".target_file", function(file) {
        bitext_file = null;
        $(".bitext_file").removeClass("dragged");
        $(".bitext_file input").val('');

        drag_callback($(".target_file"), file)
    });

    FileDnD(".bitext_file", function(file) {
        file_source = null;
        file_target = null;
        $(".source_file, .target_file").removeClass("dragged");
        $(".source_file input, .target_file input").val('');
        
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

    let adjust_languages = (el) => {
        let other = $('.lang_sel').not(el);
        let selected_lang = $(el).find('option:selected').val();
        $(other).find('option').prop('disabled', false)
        $(other).find(`option[value='${selected_lang}']`).prop('disabled', true);

        if ($(other).find('option:selected').val() == selected_lang) {
            $(other).find('option:selected').prop('selected', false);
        }
    }

    $('.source_lang').on('change', function() {
        adjust_languages(this);
    });

    adjust_languages($('.source_lang'));

    $(".data-upload-form").on("submit", function(e) {
        e.preventDefault();

        // Check if files are selected
        if (file_source == null && bitext_file == null) return false;
        if ($(".bilingual-nav-tab").hasClass("active") && (file_target == null && bitext_file == null)) return false;

        // Check file size
        if ((bitext_file != null && bitext_file.size / 1073741824 > 2) || (file_source && (file_source.size + file_target.size) / 1073741824 > 2)) {
            $(".file-size-warning").removeClass("d-none");
            return false;
        }

        $(".data-upload-form fieldset").prop("disabled", true);
        $(".token-alert").addClass("d-none");
        $(".file-size-warning").addClass("d-none");

        let data = new FormData();
        data.append("name", $("#name").val());
        data.append("description", $("#description").val());
        data.append("topic", $("#topic option:selected").val());
        data.append("source_lang", $(".source_lang option:selected").val());
        data.append("target_lang", $(".target_lang option:selected").val());

        if (bitext_file) {
            data.append("bitext_file", bitext_file)
        } else {
            data.append("source_file", file_source)
            if (file_target) data.append("target_file", file_target)
        }

        $(".file-size-warning").addClass("d-none");
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