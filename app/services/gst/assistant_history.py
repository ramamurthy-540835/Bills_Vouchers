"""Private assistant turns. Identity always comes from the authenticated session.

No shared answer cache; history is never used as a financial source of truth.
"""
import json
from uuid import uuid4

from fastapi import HTTPException

from .medallion import param


def scope_params(user_id, client_id, period):
    return [param('user', str(user_id)), param('client', str(client_id)), param('period', period)]


SCOPE = 'user_id=@user AND client_id=@client AND period=@period'


def recent(repo, user_id, client_id, period, limit=20, offset=0):
    rows = repo.query(f'''SELECT turn_id, conversation_id, question, response_json, created_at
        FROM `{repo.table('assistant_history')}` WHERE {SCOPE}
        AND created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
        ORDER BY created_at DESC, turn_id DESC LIMIT @limit OFFSET @offset''',
        [*scope_params(user_id, client_id, period), param('limit', min(50, max(1, limit)), 'INT64'), param('offset', offset, 'INT64')])
    return [dict(row.items()) for row in rows]


def conversation(repo, user_id, client_id, period, conversation_id):
    rows = repo.query(f'''SELECT question, response_json FROM `{repo.table('assistant_history')}`
        WHERE {SCOPE} AND conversation_id=@conversation
        AND created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
        ORDER BY created_at DESC, turn_id DESC LIMIT 3''',
        [*scope_params(user_id, client_id, period), param('conversation', str(conversation_id))])
    return [dict(row.items()) for row in reversed(rows)]


def save(repo, user_id, client_id, period, conversation_id, question, response):
    # A unique server ID avoids browser-provided identities and cross-user keys.
    repo.query(f'''INSERT INTO `{repo.table('assistant_history')}`
        (turn_id,user_id,client_id,period,conversation_id,question,response_json,created_at)
        VALUES (@id,@user,@client,@period,@conversation,@question,@response,CURRENT_TIMESTAMP())''',
        [param('id', uuid4().hex), *scope_params(user_id, client_id, period),
         param('conversation', str(conversation_id)), param('question', question),
         param('response', json.dumps(response, default=str))])


def clear(repo, user_id, client_id, period):
    repo.query(f'DELETE FROM `{repo.table("assistant_history")}` WHERE {SCOPE}',
               scope_params(user_id, client_id, period))


def read_response(row):
    try:
        response = json.loads(row['response_json'])
        if not isinstance(response, dict) or not isinstance(response.get('answer'), str):
            raise ValueError('Invalid stored response')
        return response
    except (ValueError, TypeError, KeyError):
        raise HTTPException(503, 'Saved assistant history could not be loaded. Please retry.') from None
