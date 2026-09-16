#include <vector>
#include <algorithm>
#include <thread>
#include <cmath>
#include <cstdio>

typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;

#define PI 3.14159265358979323846


class Crawler {
public:
    u32 r, c;
    char dR, dC;
    char dRRight, dCRight;
    char dRLeft, dCLeft;
    bool canMoveRight, canMoveLeft;
    std::vector<char> historyR;
    std::vector<char> historyC;
    u32 numBad;

    Crawler(u32 r, u32 c, char dR, char dC, char dRRight, char dCRight, char dRLeft, char dCLeft) :
        r(r), c(c), dR(dR), dC(dC), dRRight(dRRight), dCRight(dCRight), dRLeft(dRLeft), dCLeft(dCLeft), canMoveRight(true), canMoveLeft(true), numBad(0) {}

    void moveForward() {
        r += dR;
        c += dC;
        historyR.push_back(dR);
        historyC.push_back(dC);

        canMoveRight = true;
        canMoveLeft = true;
    }

    void moveRight() {
        r += dRRight;
        c += dCRight;
        historyR.push_back(dRRight);
        historyC.push_back(dCRight);

        canMoveRight = false;
        canMoveLeft = true;
    }

    void moveLeft() {
        r += dRLeft;
        c += dCLeft;
        historyR.push_back(dRLeft);
        historyC.push_back(dCLeft);

        canMoveRight = true;
        canMoveLeft = false;
    }
};


u8* floodLimited(u32 startPos, u8* mask, u32 height, u32 width, u32 limit) {
    std::vector<u32> frontier;
    frontier.push_back(startPos);

    u8* visited = (u8*)calloc(height * width, 1);
    for(u32 _ = 0; _ < limit; _++) {
        std::vector<u32> newFrontier;
        for(auto pos: frontier) {
            for(int y = -1; y < 2; y++) {
                for(int x = -1; x < 2; x++) {
                    if(y != 0 || x != 0) {
                        u32 r = pos / width + y;
                        u32 c = pos % width + x;

                        //Bounds check, don't need to check less than 0, since unsigned underflow will be greater than height and width
                        //if(r < 0 || r >= height || c < 0 || c >= width) {
                        if(r >= height || c >= width) {
                            continue;
                        }

                        u32 i = r * width + c;
                        if(mask[i] && !visited[i]) {
                            newFrontier.push_back(i);
                            visited[i] = true;
                        }
                    }
                }
            }
        }

        frontier.swap(newFrontier);
    }

    return visited;
}


void _connectionSearch(u32 pos, double targetAngle, u8 brightnessThreshold, u32 searchLimit, u8* brightnesses, u8* mask, u32 height, u32 width, std::vector<Crawler>& crawlers) {
    u8* region = floodLimited(pos, mask, height, width, searchLimit + 3);

    u32 startR = pos / width;
    u32 startC = pos % width;
    //printf("R: %d, C: %d\n", startR, startC); fflush(stdout);

    crawlers.emplace_back(startR, startC, 1, 0, 1, -1, 1, 1);
    crawlers.emplace_back(startR, startC, 1, -1, 0, -1, 1, 0);
    crawlers.emplace_back(startR, startC, 0, -1, -1, -1, 1, -1);
    crawlers.emplace_back(startR, startC, -1, -1, -1, 0, 0, -1);
    crawlers.emplace_back(startR, startC, -1, 0, -1, 1, -1, -1);
    crawlers.emplace_back(startR, startC, -1, 1, 0, 1, -1, 0);
    crawlers.emplace_back(startR, startC, 0, 1, 1, 1, -1, 1);
    crawlers.emplace_back(startR, startC, 1, 1, 1, 0, 0, 1);

    std::vector<Crawler> successfulCrawlers;
    //bool hasHit = false;
    bool hasHitOutOfRegion = false;
    //bool shouldBeOutOfRegion = false;
    u32 outOfRegionLimit = 1000;
    for(u8 i = 0; i < searchLimit; i++) {
        if(crawlers.size() == 0) {
            break;
        }
        if(crawlers.size() > crawlers.capacity() / 3) {
            break;
        }

        u32 oldLength = crawlers.size();
        for(u32 j = 0; j < oldLength; j++) {
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

        if(!hasHitOutOfRegion) {
            for(auto& c: crawlers) {
                if(c.r < height && c.c < width) {
                    u32 p = c.r * width + c.c;
                    //printf("A %d, %d, %d\n", c.r, c.c, p); fflush(stdout);
                    if(!region[p]) {
                        hasHitOutOfRegion = true;
                        outOfRegionLimit = i + 2;
                        break;
                    }
                }
            }
        }

        //printf("Crawl: %lld, %lld\n", crawlers.size(), crawlers.capacity()); fflush(stdout);

        auto newEnd = std::remove_if(crawlers.begin(), crawlers.end(), [&brightnesses, startR, startC, height, width, targetAngle, brightnessThreshold, &successfulCrawlers, &region, &mask, i, outOfRegionLimit](Crawler& c) {
            if(c.r < height && c.c < width) {
                u32 p = c.r * width + c.c;
                //printf("B %d, %d, %d\n", c.r, c.c, p); fflush(stdout);
                if(region[p] && i >= outOfRegionLimit) {
                    return true;
                }

                int dy = c.r - startR;
                int dx = startC - c.c;
                double crawlerAngle = atan2(dy, dx) + PI;

                auto angleDiff = std::min(std::abs(crawlerAngle - targetAngle), std::abs(std::abs(crawlerAngle - targetAngle) - PI * 2));

                if(angleDiff <= PI / 8) {
                    u8 b = brightnesses[p];
                    if(b >= brightnessThreshold) {
                        //printf("C %d, %d, %d\n", c.r, c.c, p); fflush(stdout);
                        if(!region[p] && mask[p]) {
                            //printf("Success: %d, %d, %f, %f, %f\n", c.r, c.c, crawlerAngle, angleDiff, targetAngle); fflush(stdout);
                            successfulCrawlers.push_back(c);
                            return true;
                        }
                        else {
                            return false;
                        }
                    }
                    else if(i < 3 && c.numBad < 1 && b >= brightnessThreshold * .95) {
                        c.numBad += 1;
                        return false;
                    }
                }
            }

            return true;
        });

        crawlers.erase(newEnd, crawlers.end());

        //if(!hasHit && )

        //printf("Crawl End: %lld, %lld\n", crawlers.size(), crawlers.capacity()); fflush(stdout);
    }

    double minAngleDiff = 1000;
    Crawler* bestCrawler = nullptr;
    for(auto& c: successfulCrawlers) {
        int dy = c.r - startR;
        int dx = startC - c.c;
        double crawlerAngle = atan2(dy, dx) + PI;

        auto angleDiff = std::min(std::abs(crawlerAngle - targetAngle), std::abs(std::abs(crawlerAngle - targetAngle) - PI * 2));
        if(angleDiff < minAngleDiff) {
            minAngleDiff = angleDiff;
            bestCrawler = &c;
        }
    }

    /*u32 maxBrightness = 0;
    Crawler* bestCrawler = nullptr;
    for(auto& c: successfulCrawlers) {
        int dy = c.r - startR;
        int dx = startC - c.c;
        double crawlerAngle = atan2(dy, dx) + PI;

        auto angleDiff = std::min(std::abs(crawlerAngle - targetAngle), std::abs(std::abs(crawlerAngle - targetAngle) - PI * 2));
        if(angleDiff < minAngleDiff + PI / 36) {
            u32 totalBrightness = 0;
            int y = startR;
            int x = startC;
            for(u32 i = 0; i < c.historyR.size(); i++) {
                auto dY = c.historyR[i];
                auto dX = c.historyC[i];

                y += dY;
                x += dX;
                u32 p = y * width + x;
                totalBrightness += brightnesses[p];
            }

            u32 avgBrightness = totalBrightness / c.historyR.size();

            if(avgBrightness > maxBrightness) {
                maxBrightness = avgBrightness;
                bestCrawler = &c;
            }
        }
    }*/

    if(bestCrawler != nullptr) {
        u32 startR = pos / width;
        u32 startC = pos % width;
        for(int y = -1; y < 2; y++) {
            for(int x = -1; x < 2; x++) {
                u32 r = startR + y;
                u32 c = startC + x;

                //Bounds check, don't need to check less than 0, since unsigned underflow will be greater than height and width
                if(r >= height || c >= width) {
                    continue;
                }

                u32 p = r * width + c;
                //printf("D %d, %d, %d\n", r, c, p); fflush(stdout);
                if(mask[p]) {
                    for(u32 i = 0; i < bestCrawler->historyR.size(); i++) {
                        int dR = bestCrawler->historyR[i];
                        int dC = bestCrawler->historyC[i];

                        r += dR;
                        c += dC;
                        if(r >= height || c >= width) {
                            break;
                        }

                        p = r * width + c;
                        //printf("E %d, %d, %d\n", dR, dC, p); fflush(stdout);
                        mask[p] = true;
                    }
                }
            }
        }
    }

    free(region);
}


extern "C" void connectionSearch(u8* brightnesses, u8* mask, u32 height, u32 width, u32 searchLimit, u32* endpoints, double* targetAngles, u8* brightnessThresholds, u32 numEndpoints) {
    std::vector<Crawler> crawlers;
    u32 MAX_CRAWLERS = 1000000;
    crawlers.reserve(MAX_CRAWLERS * 3);

    for(u32 i = 0; i < numEndpoints; i++) {
        u32 pos = endpoints[i];
        _connectionSearch(pos, targetAngles[i], brightnessThresholds[i], searchLimit, brightnesses, mask, height, width, crawlers);
        crawlers.clear();
    }
}
