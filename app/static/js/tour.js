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
    /* Activate Tour */
    const tour_id = window.location.href.split("/").length > 3 ? 
        window.location.href.split("/").slice(3).reduce((acc, v) => { acc = v ? acc + "/" + v.replace('#', '') : acc; return acc; }, "").substr(1) : null;

    if (tour_id) {
        Tour.get(tour_id, (response) => {
            let { tour } = response;
            let { tour_title, popovers } = tour;

            let steps = []
            if (popovers?.length > 0) {
                for (let popover of popovers) {
                    steps.push({
                        element: `#${popover['element']}`,
                        popover: {
                            title: popover['title'],
                            description: popover['description']
                        }
                    });
                }
            } else {
                $('.btn-begin-tour').addClass('d-none');
            }

            const driver = new Driver();
            driver.defineSteps(steps);

            $('.tour-guide-bubble').html(tour_title);

            $('.btn-begin-tour').on('click', function() {
                setTimeout(() => {
                    driver.start();
                }, 250);
            });

            $('.btn-hide-tour').on('click', function() {
                Cookies.set('hide-tour', true, { expires: 365 });
                $('.tour-guide').addClass('hidden');
            });
        });
    }
});
