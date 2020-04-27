$(document).ready(function() {
    let file_source = null;
    let file_target = null;

    let drag_callback = (e, file) => {
        if ($(e).hasClass("source_file")) {
            file_source = file
        } else {
            file_target = file
        }
    }

    FileDnD(".source_file", function(file) {
        drag_callback($(".source_file"), file)
    });

    FileDnD(".target_file", function(file) {
        drag_callback($(".target_file"), file)
    });

    $(".monolingual-nav-tab").on('click', function() {
        $(".target-file-col").addClass("target-col-disabled");
        $(".target_file").removeClass("dragged");
        $(".upload-nav-tabs .nav-link").removeClass("active");
        $(this).addClass("active");
        file_target = null;
    });

    $(".bilingual-nav-tab").on('click', function() {
        $(".target-file-col").removeClass("target-col-disabled");
        $(".upload-nav-tabs .nav-link").removeClass("active");
        $(this).addClass("active");
    });

    $(".data-upload-form").on("submit", function(e) {
        e.preventDefault();
        $(".token-alert").addClass("d-none");

        if (file_source == null) return false;

        $('.translate-form').attr('data-status', 'launching');

        let data = new FormData();
        data.append("name", $("#name").val());
        data.append("source_lang", $(".source_lang option:selected").val());
        data.append("target_lang", $(".target_lang option:selected").val());
        data.append("source_file", file_source)
        if (file_target) data.append("target_file", file_target)

        $(".token-alert").removeClass("d-none");

        $.ajax({
            url: $(this).attr("action"),
            method: 'POST',
            data: data,
            contentType: false,
            cache: false,
            processData: false,
            success: function(url) {
                window.location.href = url
            }
        });

        return false;
    });
});