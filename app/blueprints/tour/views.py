from flask import Blueprint, request, jsonify
from .ToursCollection import ToursCollection

tour_blueprint = Blueprint('tour', __name__)

@tour_blueprint.route('/get', methods=['POST'])
def tour_get():
    tour_id = request.form.get('tour_id')
    tour = ToursCollection.get(tour_id)
    if tour:
        return jsonify({ "result": 200, "tour": tour })
    else:
        return jsonify({ "result": -1 })
