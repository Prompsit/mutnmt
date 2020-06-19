class ToursCollection(object):
    tours = {
        'train': {
            'tour_title': 'It looks like you want to train an engine. Do you want help?',
            'popovers': {
                'patienceGroup': {
                    'title': 'Stopping the engine',
                    'description': 'Your engine will stop if it does not improve after this amount of validations. You can also stop the engine manually at any time.'
                },
                'vocabularySizeGroup': {
                    'title': 'Vocabulary size',
                    'description': 'The amount of words in the vocabulary is known as the vocabulary size. Using around 16K and 32K words in the vocabulary should produce good results.'
                }
            }
        }
    }

    def has(tour_id):
        return tour_id in ToursCollection.tours.keys()

    def get(tour_id):
        if ToursCollection.has(tour_id):
            return ToursCollection.tours[tour_id]
        else:
            return None