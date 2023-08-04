from flask import Blueprint, request, jsonify
from google.cloud import datastore
import json
import constants
from users import verify_jwt

client = datastore.Client()

bp = Blueprint('coordinators', __name__, url_prefix='/coordinators')

@bp.route('', methods=['POST', 'GET'])
def coordinators_get_post():
    if request.method == 'POST':
        payload = verify_jwt(request)
        content = request.get_json()
        if not all(k in content for k in ('name', 'phone_number', 'email', 'website')):
            return jsonify({'error': 'Missing fields'}), 400
        new_coordinators = datastore.entity.Entity(key=client.key(constants.coordinators))
        new_coordinators.update({
            'name': content['name'],
            'phone_number': content['phone_number'],
            'email': content['email'],
            'website': content['website'],
            'owner': payload['sub'],
            'event': None
            })
        client.put(new_coordinators)       # add new_coordinators to datastore
        new_coordinators['self'] = request.base_url + '/' + str(new_coordinators.key.id)
        new_coordinators['id'] = str(new_coordinators.key.id)
        
        return jsonify(new_coordinators), 201
    
    elif request.method == 'GET':
        payload = verify_jwt(request)
        user_sub = None
        if payload is not None:
            user_sub = payload['sub']

        query = client.query(kind=constants.coordinators)
        if user_sub is not None:
            query.add_filter('owner', '=', user_sub)

        # For pagination
        q_limit = int(request.args.get('limit', '5'))
        q_offset = int(request.args.get('limit', '0'))

        output = paginate(query, q_limit, q_offset)

        return json.dumps(output), 201
    
    else:
        return 'Method not recognized'
    
@bp.route('/<id>', methods=['GET', 'PATCH', 'DELETE'])
def coordinators_by_id(id):
    """ Routing for viewing, editing, and deleting an coordinators by ID """

    if request.method == 'GET':
        payload = verify_jwt(request)
        coordinators_key = client.key(constants.coordinators, int(id))
        coordinators = client.get(key=coordinators_key)

        if payload['sub'] != coordinators['owner']:
            return jsonify(error="Access denied"), 403
        
        coordinators['self'] = request.url_root + '/' + str(coordinators.key.id)
        if coordinators.get('events'):
            event_key = client.key(constants.events, int(coordinators['events']))
            events = client.get(key=event_key)
            if events:
                events['self'] = request.url_root + '/' + str(events.key.id)
                coordinators['events'] = events                
        
        return json.dumps(coordinators), 200

    elif request.method == 'PATCH':
        payload = verify_jwt(request)
        content = request.get_json()
        coordinators_key = client.key(constants.coordinators, int(id))
        coordinators = client.get(key=coordinators_key)
        if coordinators:
            if coordinators['owner'] != payload['sub']:
                return jsonify(error="Access denied, you do not own this event"), 403
            if 'events_id' in content:
                if coordinators.get('event') is not None:
                    return jsonify(error="The coordinators is already associated with an event"), 400
                events_key = client.key(constants.events, int(content['events_id']))
                events = client.get(key=events_key)
                if events:
                    events['coordinators'].append(coordinators.key.id)
                    client.put(events)
                    coordinators['events'] = events.key.id
                else:
                    return jsonify(error="No event with this events_id exists"), 404
                del content['events_id']

            allowed_updates = ['name', 'phone_number', 'email', 'website']
            for field in allowed_updates:
                if field in content:
                    coordinators[field] = content[field]
            client.put(coordinators)
            return jsonify(coordinators), 200
        else:
            return jsonify(error="No coordinators with this coordinators_id exists"), 404
    
    elif request.method == 'DELETE':
        payload = verify_jwt(request)
        coordinators_key = client.key(constants.coordinators, int(id))
        coordinators = client.get(key=coordinators_key)
        if coordinators:
            if coordinators['owner'] != payload['sub']:
                return jsonify(error="Access denied, you do not own this events"), 403
            if coordinators.get('events'):
                events_key = client.key(constants.events, coordinators['events'])
                events = client.get(key=events_key)
                if events:
                    events['coordinators'].remove(coordinators.key.id)
                    client.put(events)
            client.delete(coordinators_key)
            return '', 204
        else:
            return jsonify(error="No coordinators with this coordinators_id exists"), 404
    
    else:
        return 'Method not recognized'


def paginate(query, q_limit, q_offset):
    """ Helper function to paginate query """

    l_iterator = query.fetch(limit= q_limit, offset = q_offset)
    pages = l_iterator.pages
    results = list(next(pages))

    if l_iterator.next_page_token:      # Generate next page URL links
        next_offset = q_offset + q_limit
        next_url = request.base_url + '?limit=' + str(q_limit) + '&offset=' + str(next_offset)
    else:       # No pages left
        next_url = None

    for e in results:
        e['id'] = e.key.id

    output = {'coordinators': results}

    if next_url:
        output['next'] = next_url
        
    return output
