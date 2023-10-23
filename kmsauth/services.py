"""Module for accessing boto3 clients, resources and sessions."""

import boto3
import botocore
import logging

CLIENT_CACHE = {}
RESOURCE_CACHE = {}


def get_boto_client(
        client,
        region=None,
        aws_access_key_id=None,
        aws_secret_access_key=None,
        aws_session_token=None,
        endpoint_url=None,
        max_pool_connections=None,
        connect_timeout=None,
        read_timeout=None,
        ):
    """Get a boto3 client connection."""
    cache_key = '{0}:{1}:{2}:{3}'.format(
        client,
        region,
        aws_access_key_id,
        endpoint_url or ''
    )
    if not aws_session_token:
        if cache_key in CLIENT_CACHE:
            return CLIENT_CACHE[cache_key]
    session = get_boto_session(
        region,
        aws_access_key_id,
        aws_secret_access_key,
        aws_session_token
    )
    if not session:
        logging.error("Failed to get {0} client.".format(client))
        return None

    # do not explicitly set any params as None
    config_params = dict(
        max_pool_connections=max_pool_connections,
        connect_timeout=connect_timeout,
        read_timeout=read_timeout,
    )
    config_params = {k: v for (k, v) in config_params.items() if v is not None}
    CLIENT_CACHE[cache_key] = session.client(
        client,
        endpoint_url=endpoint_url,
        config=botocore.config.Config(**config_params)
    )
    return CLIENT_CACHE[cache_key]


def get_boto_resource(
        resource,
        region=None,
        aws_access_key_id=None,
        aws_secret_access_key=None,
        aws_session_token=None,
        endpoint_url=None
        ):
    """Get a boto resource connection."""
    cache_key = '{0}:{1}:{2}:{3}'.format(
        resource,
        region,
        aws_access_key_id,
        endpoint_url or ''
    )
    if not aws_session_token:
        if cache_key in RESOURCE_CACHE:
            return RESOURCE_CACHE[cache_key]
    session = get_boto_session(
        region,
        aws_access_key_id,
        aws_secret_access_key,
        aws_session_token
    )
    if not session:
        logging.error("Failed to get {0} resource.".format(resource))
        return None

    RESOURCE_CACHE[cache_key] = session.resource(
        resource,
        endpoint_url=endpoint_url
    )
    return RESOURCE_CACHE[cache_key]


def get_boto_session(
        region,
        aws_access_key_id=None,
        aws_secret_access_key=None,
        aws_session_token=None
        ):
    """Get a boto3 session."""
    return boto3.session.Session(
        region_name=region,
        aws_secret_access_key=aws_secret_access_key,
        aws_access_key_id=aws_access_key_id,
        aws_session_token=aws_session_token
    )
