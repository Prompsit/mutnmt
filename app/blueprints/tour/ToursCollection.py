class ToursCollection(object):
    tours = {
        'library/corpora': {
            'tour_title': 'Welcome to MutNMT. Let\'s get started by grabbing a public corpus or uploading a new one. Corpora will be used to train NMT engines.'
        },
        'library/engines': {
            'tour_title': 'You are in the Engines section now. Here, you can grab public engines or see your own, once you complete a training. Engines in your list will be used in Translate, Inspect and Compare sections.'
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
                    'description': 'This is the amount of epochs allowed in the training process. An epoch is a full training pass over the whole amount of sentences in the training set. Set it between 7 and 10 epochs in MutNMT.'
                },
                {
                    'element': 'patienceGroup',
                    'title': 'Stopping condition',
                    'description': 'Your engine will stop if it does not improve after a set amount of validations. Our tip for MutNMT is to set it between 3 and 5. You can also stop the engine manually at any time.'
                },
                {
                    'element': 'validationFreq',
                    'title': 'Validation frequency',
                    'description': 'The amount of steps included before an evaluation of the status of the training takes place. Validation cycles happen many times inside an epoch. A validation every 3000 and 9000 steps is what we recommend for MutNMT.'
                },
                {
                    'element': 'vocabularySizeGroup',
                    'title': 'Vocabulary size',
                    'description': 'The amount of words in the vocabulary is known as the vocabulary size. Set it between 16000 and 32000 (sub-)words in MutNMT.'
                },
                {
                    'element': 'batchSizeTxt',
                    'title': 'Batch size',
                    'description': 'The amount of tokens processed in each step is known as the batch size. This is needed because it is not possible to give the full amount of data in the training set to the neural network at once. Try with batch sizes between 6000 and 9000 tokens with MutNMT.'
                },
                {
                    'element': 'beamSizeTxt',
                    'title': 'Beam size',
                    'description': 'Number of translation hypothesis taken into account when translating a word. Set it between 6 to 8 in MutNMT.'
                },
                {
                    'element': 'corpus-selector',
                    'title': 'Corpus selector',
                    'description': 'You almost have it! The last step is to choose the corpora for the training, validation and test processes. You can choose a whole corpus or just a part of it. When you have it clear, click on the plus sign (+)'
                }
            ]
        },
        'translate': {
            'tour_title': 'Time to see your engines at work: translate using your own engine, a public one or the two at the same time. Take a  bunch of sentences, translate them and see the translation! Is this result up to your expectations?'
        },
        'inspect/details': {
            'tour_title': 'In this section, you can see how a neural engine works and compare it to others. Ideas on how to improve the results?',
            'popovers': [
                {
                    'element': 'detailsBtn',
                    'title': 'Details',
                    'description': 'Write a sentence, choose a neural engine and take a look at the whole translation process, from how it analyses that sentence to how it gives you the resulting translation.'
                },
                {
                    'element': 'compareBtn',
                    'title': 'Compare',
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
            'tour_title': 'As the name suggests, here you can evaluate translations made by machine translation engines against professional translations. You will also get familiar with automatic metrics!',
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