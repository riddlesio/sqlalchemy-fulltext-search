# -*- coding: utf-8 -*-s

from __future__ import absolute_import

import re

from sqlalchemy import event, literal
from sqlalchemy.schema import DDL
from sqlalchemy.orm.mapper import Mapper
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.expression import ClauseElement
from . import modes as FullTextMode


MYSQL = 'mysql'
MYSQL_BUILD_INDEX_QUERY = u'ALTER TABLE {0.__tablename__} ADD FULLTEXT ({1})'
MYSQL_MATCH_AGAINST = u'MATCH ({0}) AGAINST ({1} {2})'


def escape_quote(string):
    return re.sub(r'[\"\']+', '', string)


class FullTextSearch(ClauseElement):
    """
    Search FullText
    :param against: the search query
    :param model: the model to query against
    :param mode: mode to perform match
    """
    def __init__(self, against, model, mode=FullTextMode.DEFAULT):
        self.against = literal(against)
        self.model = model
        self.mode = mode


def get_table_name(element):
    if hasattr(element.model, '_aliased_insp'):
        # noinspection PyProtectedMember
        return '`{}`'.format(element.model._aliased_insp.name)
    elif hasattr(element.model, '__table__'):
        return '`{}`'.format(element.model.__table__.fullname)
    return ''


@compiles(FullTextSearch, MYSQL)
def __mysql_fulltext_search(element, compiler, **kw):
    assert issubclass(element.model, FullText), '{0} not FullTextable'.format(element.model)

    table_name = get_table_name(element)
    fulltext_columns = element.model.__fulltext_columns__
    return MYSQL_MATCH_AGAINST.format(
        ', '.join(['{}.{}'.format(table_name, c) for c in fulltext_columns]),
        compiler.process(element.against),
        element.mode
    )


class FullText(object):
    __fulltext_columns__ = tuple()

    @classmethod
    def build_fulltext(cls):
        """
        build up fulltext index after table is created
        """
        if FullText not in cls.__bases__:
            return
        assert cls.__fulltext_columns__, 'Model:{0.__name__} No FullText columns defined'.format(cls)

        event.listen(
            cls.__table__,
            'after_create',
            DDL(MYSQL_BUILD_INDEX_QUERY.format(
                cls,
                ', '.join((escape_quote(c) for c in cls.__fulltext_columns__))
            ))
        )
    """
    TODO: black magic in the future
    @classmethod
    @declared_attr
    def __contains__(*arg):
        return True
    """


def __build_fulltext_index(mapper, class_):    
    if issubclass(class_, FullText):
        class_.build_fulltext()


event.listen(Mapper, 'instrument_class', __build_fulltext_index)
