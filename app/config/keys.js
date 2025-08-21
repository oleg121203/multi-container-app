module.exports = {
    // Prefer environment variable if provided, fallback to compose service name
    mongoProdURI: process.env.MONGO_URI || 'mongodb://todo-database:27017/todoapp',
};