/**
 * GLTFLoader Placeholder
 * This is a minimal placeholder for Three.js GLTFLoader
 */

// GLTFLoader class placeholder
window.GLTFLoader = window.GLTFLoader || function() {
    this.load = function(url, onLoad, onProgress, onError) {
        console.warn('GLTFLoader placeholder - 3D model loading not available');
        if (onError) {
            onError(new Error('GLTFLoader not available (using placeholder)'));
        }
    };
    
    this.parse = function(data, path, onLoad, onError) {
        console.warn('GLTFLoader.parse placeholder');
        if (onError) {
            onError(new Error('GLTFLoader.parse not available (using placeholder)'));
        }
    };
};

console.log('GLTFLoader placeholder loaded');