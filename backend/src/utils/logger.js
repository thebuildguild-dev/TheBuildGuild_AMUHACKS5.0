export const log = {
    info: (message, ...args) => {
        console.log(`[INFO] ${message}`, ...args);
    },

    success: (message, ...args) => {
        console.log(`✓ ${message}`, ...args);
    },

    warn: (message, ...args) => {
        console.warn(`⚠ ${message}`, ...args);
    },

    error: (message, ...args) => {
        console.error(`✗ ${message}`, ...args);
    },

    debug: (message, ...args) => {
        if (process.env.NODE_ENV === 'development') {
            console.log(`[DEBUG] ${message}`, ...args);
        }
    },
};

export default log;
