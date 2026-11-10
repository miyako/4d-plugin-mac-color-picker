#pragma once

// Test-only platform boundary: Foundation text/data, never real AppKit.
#import <Foundation/Foundation.h>
#import <CoreGraphics/CoreGraphics.h>

@interface NSImage : NSObject
- (id)initWithCGImage:(CGImageRef)image size:(NSSize)size;
- (NSData *)TIFFRepresentation;
@end
