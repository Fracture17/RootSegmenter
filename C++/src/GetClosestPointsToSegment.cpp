#include <vector>
#include <cstdio>
#include <cmath>
#include <set>


typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;


void floodFillClosest(u32 startPos, u8* mask, u8* segment, int* closestPointsR, int* closestPointsC, u8* results, u32 height, u32 width) {
    std::vector<u32> frontier;
    frontier.push_back(startPos);
    std::set<u32> used;
    used.insert(startPos);
    results[startPos] = true;

    int limit = 1000;
    for(int i = 0; i < limit; i++) {
        //printf("V: %d, %d, %d, %d\n", startPos / width, startPos % width, i, int(frontier.size())); fflush(stdout);
        std::vector<u32> newFrontier;
        for(auto p: frontier) {
            for(int y = -1; y < 2; y++) {
                for(int x = -1; x < 2; x++) {
                    if(y != 0 || x != 0) {
                        u32 r = p / width + y;
                        u32 c = p % width + x;
                        if(r < height && c < width) {
                            u32 newPos = r * width + c;
                            if(mask[newPos] && used.count(newPos) == 0) {
                                used.insert(newPos);

                                u32 closestR = closestPointsR[newPos];
                                u32 closestC = closestPointsC[newPos];
                                u32 closestPos = closestR * width + closestC;

                                if(segment[closestPos]) {
                                    newFrontier.push_back(newPos);
                                    results[newPos] = true;
                                }
                            }
                        }
                    }
                }
            }
        }

        frontier.swap(newFrontier);
    }
}


extern "C" void getClosestPointsToSegment(u8* mask, u8* segment, int* closestPointsR, int* closestPointsC, u8* results, u32 height, u32 width) {
    for(u32 r = 0; r < height; r++) {
        for(u32 c = 0; c < width; c++) {
            u32 p = r * width + c;
            if(segment[p]) {
                floodFillClosest(p, mask, segment, closestPointsR, closestPointsC, results, height, width);
            }
        }
    }
}