export const sendSuccess = (res, data = null, message = 'Success', statusCode = 200) => {
    const response = {
        success: true,
        message,
    };

    if (data !== null) {
        response.data = data;
    }

    return res.status(statusCode).json(response);
};

export const sendError = (res, message = 'Internal Server Error', statusCode = 500, error = null) => {
    const response = {
        success: false,
        error: getErrorName(statusCode),
        message,
    };

    if (error && process.env.NODE_ENV === 'development') {
        response.details = error.message;
    }

    return res.status(statusCode).json(response);
};

export const sendCreated = (res, data, message = 'Resource created successfully') => {
    return sendSuccess(res, data, message, 201);
};

export const sendNotFound = (res, message = 'Resource not found') => {
    return sendError(res, message, 404);
};

export const sendBadRequest = (res, message = 'Bad request') => {
    return sendError(res, message, 400);
};

export const sendUnauthorized = (res, message = 'Unauthorized') => {
    return sendError(res, message, 401);
};

export const sendForbidden = (res, message = 'Forbidden') => {
    return sendError(res, message, 403);
};

export const sendConflict = (res, message = 'Resource already exists') => {
    return sendError(res, message, 409);
};

export const sendServiceUnavailable = (res, message = 'Service temporarily unavailable') => {
    return sendError(res, message, 503);
};

export const sendGatewayTimeout = (res, message = 'Gateway timeout') => {
    return sendError(res, message, 504);
};

const getErrorName = (statusCode) => {
    const errorNames = {
        400: 'Bad Request',
        401: 'Unauthorized',
        403: 'Forbidden',
        404: 'Not Found',
        409: 'Conflict',
        500: 'Internal Server Error',
        503: 'Service Unavailable',
        504: 'Gateway Timeout',
    };

    return errorNames[statusCode] || 'Error';
};

export const handleDatabaseError = (res, error, customMessage = 'Database operation failed') => {
    console.error('Database error:', error);

    if (error.code === '23505') {
        return sendConflict(res, 'Resource already exists');
    }

    if (error.code === '23502') {
        return sendBadRequest(res, 'Missing required field');
    }

    if (error.code === '23503') {
        return sendBadRequest(res, 'Referenced resource does not exist');
    }

    return sendError(res, customMessage, 500, error);
};

export const validateRequired = (fields, data) => {
    const missing = [];

    for (const field of fields) {
        if (!data[field]) {
            missing.push(field);
        }
    }

    return missing.length > 0 ? missing : null;
};
