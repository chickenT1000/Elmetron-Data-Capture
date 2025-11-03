"""
Add this endpoint after the rename_session endpoint in data_api_service.py
"""

endpoint_code = '''
@app.route('/api/sessions/<int:session_id>/operator', methods=['PATCH'])
def update_session_operator(session_id: int):
    """
    Update operator name for a session.
    
    Request body:
        {
            "operator_name": "John Doe"
        }
    
    Returns:
        {
            "id": 1,
            "operator_name": "John Doe",
            "updated_at": "2025-10-29T12:34:56Z"
        }
    """
    try:
        data = request.get_json()
        if not data or 'operator_name' not in data:
            return jsonify({'error': 'Missing "operator_name" in request body'}), 400
        
        operator_name = data['operator_name']
        
        # Validation
        if operator_name is not None and not isinstance(operator_name, str):
            return jsonify({'error': 'Operator name must be a string or null'}), 400
        
        # Sanitize
        if operator_name:
            operator_name = operator_name.strip()
            if len(operator_name) > 100:
                return jsonify({'error': 'Operator name must be 100 characters or less'}), 400
            if len(operator_name) == 0:
                operator_name = None
        else:
            operator_name = None
        
        # Update in database
        conn = sqlite3.connect(str(db.path))
        try:
            cursor = conn.cursor()
            
            # Check if session exists
            cursor.execute("SELECT id FROM sessions WHERE id = ?", (session_id,))
            if not cursor.fetchone():
                return jsonify({'error': f'Session {session_id} not found'}), 404
            
            # Update operator name
            cursor.execute(
                "UPDATE sessions SET operator_name = ? WHERE id = ?",
                (operator_name, session_id)
            )
            conn.commit()
            
            return jsonify({
                'id': session_id,
                'operator_name': operator_name,
                'updated_at': datetime.utcnow().isoformat() + 'Z'
            })
        finally:
            conn.close()
    
    except Exception as e:
        logger.error(f"Error updating operator for session {session_id}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500
'''

print(endpoint_code)
