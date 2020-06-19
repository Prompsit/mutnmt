(function() {
    window.Tour = {
        get: (tour_id, success, error) => {
            fetch('/tour/get', { 
                method: 'POST',
                body: new URLSearchParams(`tour_id=${tour_id}`)
            }).then(response => response.json())
            .then(response => {
                if (response.result == 200) {
                    if (Cookies.get('hide-tour') != "true") {
                        $('.tour-guide').removeClass('hidden');
                    }
                    
                    $('.btn-begin-tour').removeClass('d-none'); // To show it on phones
                    success(response);
                } else if (error) {
                    error(response);
                }
            })
            .catch(e => {
                if (error) { error(e) }
            });
        }
    }
})(window);

$(document).ready(function() {
    $('.btn-hide-tour').on('click', function() {
        Cookies.set('hide-tour', true, { expires: 365 });
        $('.tour-guide').addClass('hidden');
    });
});
