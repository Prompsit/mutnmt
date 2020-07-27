$(document).ready(function() {
    $('.custom-file input[type=file]').each(function (i, el) {
        if (el.files.length > 0) {
            $(el).closest(".custom-file").find(".custom-file-label").html(el.files[0].name);
        }
    });
    
    $('.custom-file input[type=file]').on('change', function() {
        $(this).closest(".custom-file").find(".custom-file-label").html(this.files[0].name);
        $(this).closest(".custom-file").attr("title", this.files[0].name);
    });
});