$(document).ready(function() {
    $('.custom-file-input').on('change', function(e) {
        let fullpath = $(this).val()
        let startIndex = (fullpath.indexOf('\\') >= 0 ? fullpath.lastIndexOf('\\') : fullpath.lastIndexOf('/'));
        let filename = fullpath.substring(startIndex);
        if (filename.indexOf('\\') === 0 || filename.indexOf('/') === 0) {
            filename = filename.substring(1);
        }

        $(this).siblings('.custom-file-label').html(filename);
    })
});