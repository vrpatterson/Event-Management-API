from flask import Blueprint, request, jsonify
from google.cloud import datastore
import json
import constants
from users import verify_jwt

client = datastore.Client()

bp = Blueprint('events', __name__, url_prefix='/events')

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

    output = {'events': results}

    if next_url:
        output['next'] = next_url
        
    return output

@bp.route('', methods=['POST', 'GET'])
def events_get_post():
    """ Routing for posting a new event and viewing all events """

    if request.method == 'POST':
        payload = verify_jwt(request)
        content = request.get_json()
        if not all(k in content for k in ('name', 'description', 'date-time', 'location')):
            return jsonify({'error': 'Missing fields'}), 400
        new_event = datastore.entity.Entity(key=client.key(constants.events))
        new_event.update({
            'name': content['name'], 
            'description': content['description'], 
            'date-time': content['date-time'],
            'location': content['location'], 
            'event_host_id':payload['sub'],
            'coordinators': []
            })
        client.put(new_event)       # add new_event to datastore
        new_event['self'] = request.base_url + '/' +str(new_event.key.id)
        new_event['id'] = str(new_event.key.id)
        return jsonify(new_event), 201
    
    elif request.method == 'GET':
        payload = verify_jwt(request)
        user_sub = None
        if payload is not None:
            user_sub = payload['sub']

        query = client.query(kind=constants.events)
        if user_sub is not None:
            query.add_filter('event_host_id', '=', user_sub)

        # For pagination
        q_limit = int(request.args.get('limit', '5'))
        q_offset = int(request.args.get('limit', '0'))

        output = paginate(query, q_limit, q_offset)

        return json.dumps(output), 201
    
    else:
        return 'Method not recognized'
    
@bp.route('/<id>', methods=['GET', 'PATCH', 'DELETE'])
def event_by_id(id):
    """ Routing for viewing, editing, and deleting an event by ID """

    if request.method == 'GET':
        payload = verify_jwt(request)
        event_key = client.key(constants.events, int(id))
        event = client.get(key=event_key)

        if not event:
            return jsonify(error="No event with this id exists"), 404
        if payload['sub'] != event['event_host_id']:
            return jsonify(error="Access denied, you do not own this event")
        
        event['self'] = request.url_root + '/' + str(event.key.id)
        return jsonify(event), 200

    elif request.method == 'PATCH':
        content = request.get_json()
        event_key = client.key(constants.events, int(id))
        event = client.get(key=event_key)
        if not event:
            return 'No event found with this ID'
        
        event.update(content)
        client.put(event)
        return jsonify(event), 200
    
    elif request.method == 'DELETE':
        key = client.key(constants.events, int(id))
        if not key:
            return 'No event found with this ID'
        client.delete(key)
        return('', 204)
    
    else:
        return 'Method not recognized'
