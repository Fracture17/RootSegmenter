#include <vector>
#include <map>
#include <cstdio>
#include <cmath>
#include <set>


typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;


std::vector<u32> getNeighbors(u32 startPos, u8* mask, std::set<u32>& used, u32 height, u32 width) {
    std::vector<u32> neighbors;
    u32 startR = startPos / width;
    u32 startC = startPos % width;
    for(int y = -1; y < 2; y++) {
        for(int x = -1; x < 2; x++) {
            if(y != 0 || x != 0) {
                u32 r = startR + y;
                u32 c = startC + x;
                if(r < height && c < width) {
                    u32 newPos = r * width + c;
                    //printf("N: %d, %d\n", newPos / width, newPos % width); fflush(stdout);
                    if(used.count(newPos) == 0) {
                        //printf("N2: %d, %d\n", newPos / width, newPos % width); fflush(stdout);
                        if(mask[newPos]) {
                            //printf("N3: %d, %d\n", newPos / width, newPos % width); fflush(stdout);
                            neighbors.push_back(newPos);
                        }
                    }
                }
            }
        }
    }

    return neighbors;
}


void _getClosestSkeleton(u32 startPos, u8* mask, u8* skeleton, int* resultsR, int* resultsC, u32 height, u32 width) {
    std::vector<u32> frontier;
    frontier.push_back(startPos);
    std::map<u32, float> distances;
    distances[startPos] = 0;
    int limit = 1000;
    double minDistance = 9999999;
    u32 bestPos = 0;

    for(int i = 0; i < limit; i++) {
        std::vector<u32> newFrontier;
        for(auto p: frontier) {
            for(int y = -1; y < 2; y++) {
                for(int x = -1; x < 2; x++) {
                    if(y != 0 || x != 0) {
                        u32 r = p / width + y;
                        u32 c = p % width + x;
                        if(r < height && c < width) {
                            u32 newPos = r * width + c;
                            if(mask[newPos]) {
                                auto currentDistance = distances[p];
                                //printf("V2: %d, %d, %d, %d, %d, %d, %f\n", startPos / width, startPos % width, r, c, y, x, currentDistance); fflush(stdout);
                                if(y == 0 || x == 0) {
                                    currentDistance += 1;
                                }
                                else {
                                    currentDistance += 1.414;
                                }
                                //printf("V3: %d, %d, %d, %d, %d, %d, %f\n", startPos / width, startPos % width, r, c, y, x, currentDistance); fflush(stdout);

                                if(distances.count(newPos) == 1) {
                                    auto d = distances[newPos];
                                    if(currentDistance < d) {
                                        distances[newPos] = currentDistance;
                                    }
                                }
                                else {
                                    distances[newPos] = currentDistance;
                                }
                                //printf("V4: %d, %d, %d, %d, %d, %d, %f, %f\n", startPos / width, startPos % width, r, c, p / width, p % width, currentDistance, distances[newPos]); fflush(stdout);

                                auto d = distances[newPos];
                                if(d == currentDistance) {
                                    //printf("V: %d, %d, %d, %d, %d, %d, %f\n", startPos / width, startPos % width, r, c, y, x, d); fflush(stdout);
                                    if(skeleton[newPos]) {
                                        if(d < minDistance) {
                                            //printf("D2: %d, %d, %d, %d, %d, %d, %f\n", startPos / width, startPos % width, r, c, y, x, d); fflush(stdout);
                                            bestPos = newPos;
                                            minDistance = d;
                                            limit = int(d + 1);
                                        }
                                    }
                                    else {
                                        newFrontier.push_back(newPos);
                                    }
                                }

                            }
                        }
                    }
                }
            }
        }
        frontier.swap(newFrontier);
    }

    if(limit < 1000) {
        u32 r = bestPos / width;
        u32 c = bestPos % width;
        //printf("R: %d, %d, %d, %d\n", startPos / width, startPos % width, r, c); fflush(stdout);
        resultsR[startPos] = r;
        resultsC[startPos] = c;
    }
    else {
        //printf("No Neighbors found: %d, %d\n", startPos / width, startPos % width); fflush(stdout);
    }
}


extern "C" void getClosestSkeleton(u8* mask, u8* skeleton, int* resultsR, int* resultsC, u32 height, u32 width) {
    for(u32 r = 0; r < height; r++) {
        for(u32 c = 0; c < width; c++) {
            u32 p = r * width + c;
            if(mask[p]) {
                if(skeleton[p]) {
                    resultsR[p] = r;
                    resultsC[p] = c;
                    //printf("R2: %d, %d, %d, %d\n", p / width, p % width, r, c); fflush(stdout);
                }
                else {
                    _getClosestSkeleton(p, mask, skeleton, resultsR, resultsC, height, width);
                }
            }
        }
    }
}