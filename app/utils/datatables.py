from sqlalchemy import desc, asc, or_
from flask import jsonify
from sqlalchemy.orm import load_only

class Datatables(object):
    def __init__(self):
        self.draw = None
        self.search = None

    def parse(self, table, columns, request, condition = None):
        self.draw = request.form.get('draw')
        self.search = request.form.get('search[value]')
        start = request.form.get('start')
        length = request.form.get('length')
        order = int(request.form.get('order[0][column]'))
        dir = request.form.get('order[0][dir]')

        rows = table.query.options(load_only(*columns))

        if condition is not None:
            rows = rows.filter(condition)

        rows = rows.order_by(asc(columns[order]) if dir == "asc" else desc(columns[order])) \
                .limit(length).offset(start) \
                .all()
    
        rows_filtered = None
        if self.search:
            rows_filtered = table.query.options(load_only(*columns)) \
                                .filter(or_(*[c.ilike('%{}%'.format(self.search)) for c in columns])) \
                                .order_by(asc(columns[order]) if dir == "asc" else desc(columns[order])) \
                                .limit(length).offset(start) \
                                .all()


        return rows, rows_filtered, self.search

    def response(self, rows, rows_filtered, data):
        return jsonify({
            "draw": int(self.draw) + 1,
            "recordsTotal": len(rows),
            "recordsFiltered": len(rows_filtered) if self.search else len(rows),
            "data": data
        })