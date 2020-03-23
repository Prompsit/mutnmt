$(document).ready(function() {
    let dragged_file = null;
    FileDnD(".file-dnd", function(file) {
        dragged_file = file;
    });

    $(".translate-file-form").on("submit", function(e) {
        e.preventDefault();
        if (dragged_file == null) return false;

        $('.translate-form').attr('data-status', 'launching');

        let data = new FormData();
        data.append("user_file", dragged_file);
        data.append("engine_id", $(".engine-select option:selected").val());
        data.append("as_tmx", $("#as_tmx").val());

        $.ajax({
            url: $(this).attr("action"),
            method: 'POST',
            data: data,
            contentType: false,
            cache: false,
            processData: false,
            success: function(key_url) {
                $(".file_download").attr("href", key_url);
                $('.translate-form').attr('data-status', 'ready');
            }
        });

        return false;
    });

    $('.translate-btn').on('click', function() {
        $("#as_tmx").val($(this).hasClass("translate-tmx-btn"));
        $(this).closest('form').trigger('submit');
    });
})