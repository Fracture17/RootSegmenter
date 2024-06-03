typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;


extern "C" void gaussianThreshold(u8* smoothed, u8* brightnesses, u8* results, double threshold, u32 height, u32 width) {
    for(u32 r = 0; r < height; r++) {
        for(u32 c = 0; c < width; c++) {
            u32 i = r * width + c;
            u8 b = brightnesses[i];
            u8 b2 = smoothed[i];
            if(b > b2 * threshold) {
                results[i] = true;
            }
        }
    }
}
