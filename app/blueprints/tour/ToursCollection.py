class ToursCollection(object):
    tours = {
        'library/corpora': {
            'tour_title': 'Welcome to MuNMT. This section is all about Data. You should start by grabbing a corpus from Public data or uploading a new one. Corpora will be used to train engines.'
        },
        'library/engines': {
            'tour_title': 'You are in the Engines section now. You should start by grabbing a public engine or training a new one in the Train section to be able to Translate, Inspect and Compare NMT systems.'
        },
        'train': {
            'tour_title': 'It looks like you want to train an engine. Do you want help?',
            'popovers': [
                {
                    'element': 'nameText',
                    'title': 'Name your neural engine'
                },
                {
                    'element': 'source_lang',
                    'title': 'Source and target languages',
                    'description': 'Choose the source and target language of your neural engine. Make sure you have corpora available for the selected languages.'
                },
                {
                    'element': 'descriptionText',
                    'title': 'Description',
                    'description': 'You can write a brief description about your neural engine. Maybe you can say whether it is a generic or a custom engine.'
                },
                {
                    'element': 'epochsText',
                    'title': 'Duration',
                    'description': 'The amount of epochs allowed in the training process. An epoch is a full training pass over the whole amount of sentences in the training set. An epoch comprises the necessary number of training steps using the batch size to see all the data once.  Around (7) to (10) epochs should produce good results with MutNMT.'
                },
                {
                    'element': 'patienceGroup',
                    'title': 'Stopping the engine',
                    'description': 'Your engine will stop if it does not improve after this amount of validations. You can also stop the engine manually at any time.'
                },
                {
                    'element': 'vocabularySizeGroup',
                    'title': 'Vocabulary size',
                    'description': 'The amount of words in the vocabulary is known as the vocabulary size. Using around 16K and 32K words in the vocabulary should produce good results.'
                },
                {
                    'element': 'batchSizeTxt',
                    'title': 'Batch size',
                    'description': 'The amount of tokens processed in each step is known as the batch size. This is needed because it is not possible to give the full amount of data in the training set to the neural network at once. It produces good results with, say between 6,000 and 12,0000 tokens.'
                },
                {
                    'element': 'corpus-selector',
                    'title': 'Corpus selector',
                    'description': 'You almost have it! The last step is to choose the corpora for the training, validation and test processes. You can choose a whole corpus or just a part of it. When you have it clear, click on the plus sign (+)'
                }
            ]
        },
        'translate': {
            'tour_title': 'You can now translate with the neural engine you have trained, with one you have grabbed from “Public engines”, or even with two at the same time. Take a bunch of sentences, translate them and take a look at the resulting translation! Is this result up to your expectations?'
        },
        'inspect/details': {
            'tour_title': 'In this section, you can inspect a neural engine to know how to improve it.',
            'popovers': [
                {
                    'element': 'detailsBtn',
                    'title': 'Details',
                    'description': 'Write a sentence, choose a neural engine and take a look at the whole translation process, from how it analyses that sentence to how it gives you the resulting translation.'
                },
                {
                    'element': 'compareBtn',
                    'title': 'Details',
                    'description': 'Write a sentence, choose a neural engine and compare the resulting translation with another neural engine. Both engines must have the same source and target languages.'
                },
                {
                    'element': 'accessBtn',
                    'title': 'Access',
                    'description': 'Yet to come!'
                }
            ]
        },
        'evaluate': {
            'tour_title': 'You are in the Evaluate section. As the name suggests, here you can evaluate the translation made by the neural engine.',
            'popovers': [
                {
                    'element': 'source_file',
                    'title': 'Source file (optional)',
                    'description': 'Original text should be plain text or TMX'
                },
                {
                    'element': 'mt_file',
                    'title': 'Machine translation',
                    'description': 'Translation made by the neural engine. It should be plain text or TMX.'
                },
                {
                    'element': 'ht_file',
                    'title': 'Reference translation',
                    'description': 'Translation performed by a professional. It should be plain text or TMX.'
                }
            ]
        }
    }

    @staticmethod
    def has(tour_id):
        return tour_id in ToursCollection.tours.keys()

    @staticmethod
    def get(tour_id):
        if ToursCollection.has(tour_id):
            return ToursCollection.tours[tour_id]
        else:
            return None