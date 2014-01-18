#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'ivan'

CREATE_GAME_JSON = '''{
    "title": "A game",
    "version": 5,
    "players": [
        {
            "id": "1",
            "name": "Vasya",
            "words": [
                {
                    "text": "hat",
                    "origin": "MANUAL_INPUT"
                },
                {
                    "text": "hair",
                    "origin": "RANDOM"
                }
            ]
        }
    ],
    "words": [
        {
            "text": "banana",
            "origin": "PACKAGE"
        },
        {
            "text": "tea",
            "origin": "RANDOM"
        }
    ],
    "meta": {
        "time_per_round": 20,
        "words_per_player": 10,
        "skip_count": 1
    },
    "order": [
        "1"
    ]
}
'''

GAME_JSON = '''
    "title": "A game",
    "version": 5,
    "players": [
        {
            "id": "1",
            "name": "Vasya",
            "words": [
                {
                    "text": "hat",
                    "origin": "MANUAL_INPUT"
                },
                {
                    "text": "hair",
                    "origin": "RANDOM"
                }
            ]
        },
        {
            "id": "2",
            "name": "Petya",
            "words": [
                {
                    "text": "hater",
                    "origin": "MANUAL_INPUT"
                },
                {
                    "text": "pig",
                    "origin": "RANDOM"
                }
            ]
        }
    ],
    "words": [
        {
            "text": "banana",
            "origin": "PACKAGE"
        },
        {
            "text": "tea",
            "origin": "RANDOM"
        }
    ],
    "meta": {
        "time_per_round": 20,
        "words_per_player": 10,
        "skip_count": 1
    },
    "order": [
        "1", "2"
    ]
}
'''

UPDATE_META_JSON = '''
    {
        "updated_meta":
        {
            "time_per_round": 25,
            "words_per_player": 2,
            "skip_count": 0
        }
    }
'''

DELETE_PLAYERS_JSON = '''
    {
        "players_delete": [
            "1"
        ]
    }
'''
