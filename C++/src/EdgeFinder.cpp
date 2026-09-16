#include <vector>
#include <algorithm>
#include <thread>
#include <cstdio>


typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;


class Crawler {
public:
    u32 r, c;
    char dR, dC;
    char dRRight, dCRight;
    char dRLeft, dCLeft;
    bool canMoveRight, canMoveLeft;

    Crawler(u32 r, u32 c, char dR, char dC, char dRRight, char dCRight, char dRLeft, char dCLeft) :
        r(r), c(c), dR(dR), dC(dC), dRRight(dRRight), dCRight(dCRight), dRLeft(dRLeft), dCLeft(dCLeft), canMoveRight(true), canMoveLeft(true) {}

    void moveForward() {
        r += dR;
        c += dC;

        canMoveRight = true;
        canMoveLeft = true;
    }

    void moveRight() {
        r += dRRight;
        c += dCRight;

        canMoveRight = false;
        canMoveLeft = true;
    }

    void moveLeft() {
        r += dRLeft;
        c += dCLeft;

        canMoveRight = true;
        canMoveLeft = false;
    }
};


void _checkForEdge(u8* brightnesses, u8* edgeHit, u32 maxDistance, double upperThreshold, double lowerThreshold, double hardEdgeThreshold, u32 r, u32 c, u32 height, u32 width, std::vector<Crawler>& crawlers) {
    crawlers.emplace_back(r, c, 1, 0, 1, -1, 1, 1);
    crawlers.emplace_back(r, c, 1, -1, 0, -1, 1, 0);
    crawlers.emplace_back(r, c, 0, -1, -1, -1, 1, -1);
    crawlers.emplace_back(r, c, -1, -1, -1, 0, 0, -1);
    crawlers.emplace_back(r, c, -1, 0, -1, 1, -1, -1);
    crawlers.emplace_back(r, c, -1, 1, 0, 1, -1, 0);
    crawlers.emplace_back(r, c, 0, 1, 1, 1, -1, 1);
    crawlers.emplace_back(r, c, 1, 1, 1, 0, 0, 1);

    u32 initialPosition = r * width + c;
    u16 initialBrightness = brightnesses[initialPosition];
    double initialLowBrightnessThreshold = initialBrightness * upperThreshold;
    double softEdgeBrightnessThreshold = initialLowBrightnessThreshold;
    double hardEdgeBrightnessThreshold = initialBrightness * hardEdgeThreshold;

    for(u8 i = 0; i < maxDistance; i++) {
        if(crawlers.size() == 0) {
            break;
        }
        //if(crawlers.size() > crawlers.capacity() / 3) {
        if(crawlers.size() > 10000000) {
            break;
        }

        u32 oldLength = crawlers.size();
        for(u32 j = 0; j < oldLength; j++) {
            //Don't need to care about reallocation because or large reserve
            auto& c = crawlers[j];

            if(c.canMoveRight) {
                crawlers.push_back(c);
                crawlers.back().moveRight();
            }

            if(c.canMoveLeft) {
                crawlers.push_back(c);
                crawlers.back().moveLeft();
            }

            c.moveForward();
        }

        u32 lowestBrightness = 1000;
        for(auto& c : crawlers) {
            u32 p = c.r * width + c.c;

            if(brightnesses[p] < lowestBrightness) {
                lowestBrightness = brightnesses[p];
            }
        }

        softEdgeBrightnessThreshold = std::min(softEdgeBrightnessThreshold, lowestBrightness * lowerThreshold);
        softEdgeBrightnessThreshold = std::min(softEdgeBrightnessThreshold, double(initialBrightness));

        auto newEnd = std::remove_if(crawlers.begin(), crawlers.end(), [&brightnesses, &edgeHit, softEdgeBrightnessThreshold, hardEdgeBrightnessThreshold, width](const Crawler& c) {
            u32 p = c.r * width + c.c;
            u16 b = brightnesses[p];

            if(b < hardEdgeBrightnessThreshold) {
                edgeHit[p] |= 2;
                return true;
            }
            if(b < softEdgeBrightnessThreshold) {
                edgeHit[p] |= 1;
                return true;
            }

            return false;
        });

        crawlers.erase(newEnd, crawlers.end());
    }
}


extern "C" void checkForEdgesParallel(u8* brightnesses, u8* edgeHit, u32* targets, u32 numTargets, u32 maxDistance, double upperThreshold, double lowerThreshold, double hardEdgeThreshold, u32 height, u32 width) {
    std::vector<Crawler> crawlers;
    u32 MAX_CRAWLERS = 10000000;
    crawlers.reserve(MAX_CRAWLERS * 3);

    for(u32 i = 0; i < numTargets; i++) {
        u32 p = targets[i];
        u32 r = p / width;
        u32 c = p % width;
        _checkForEdge(brightnesses, edgeHit, maxDistance, upperThreshold, lowerThreshold, hardEdgeThreshold, r, c, height, width, crawlers);
        crawlers.clear();
    }
}

extern "C" void checkForEdges(u8* brightnesses, u8* edgeHit, u32* targets, u32 numTargets, u32 maxDistance, double upperThreshold, double lowerThreshold, double hardEdgeThreshold, u32 height, u32 width) {
    u32 cores = std::thread::hardware_concurrency();
    if(cores == 0) {
        cores = 6;
    }

    std::vector<std::thread> threads;
    u8** results = new u8*[cores];
    for(u32 i = 0; i < cores; i++) {
        u32 n = numTargets / cores;
        if((numTargets % cores) > i) {
            n++;
        }
        results[i] = new u8[height * width];
        threads.push_back(std::thread(checkForEdgesParallel, brightnesses, results[i], targets, n, maxDistance, upperThreshold, lowerThreshold, hardEdgeThreshold, height, width));
        targets += n;
    }

    for (u32 i = 0; i < cores; i++) {
        threads[i].join();
        for(u32 j = 0; j < height * width; j++) {
            edgeHit[j] |= results[i][j];
        }
        delete[] results[i];
    }
    delete[] results;

    /*for (u32 i = 0; i < cores; i++) {
        for(u32 j = 0; j < height * width; j++) {
            edgeHit[j] |= results[i][j];
        }
        delete[] results[i];
    }
    delete[] results;*/

    /*for(u32 i = 0; i < numTargets; i++) {
        u32 p = targets[i];
        u32 r = p / width;
        u32 c = p % width;
        _checkForEdge(brightnesses, edgeHit, maxDistance, upperThreshold, lowerThreshold, r, c, height, width, crawlers);
        crawlers.clear();
    }*/

    /*for(u32 r = 20; r < height - 20; r++) {
        for(u32 c = 20; c < width - 20; c++) {
            u32 i = r * width + c;
            if(targets[i]) {
                _checkForEdge(brightnesses, edgeHit, maxDistance, upperThreshold, lowerThreshold, r, c, height, width, crawlers);
                crawlers.clear();
            }
        }
    }*/
}
