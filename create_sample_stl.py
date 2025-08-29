#!/usr/bin/env python
"""
Create a simple STL file for testing the viewer.
This creates a basic cube STL file.
"""

def create_cube_stl(filename="sample_cube.stl"):
    """Create a simple cube STL file in ASCII format."""
    
    # Define the 8 vertices of a cube
    vertices = [
        [0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],  # bottom face
        [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]   # top face
    ]
    
    # Define the 12 triangles (2 per face, 6 faces)
    triangles = [
        # Bottom face
        ([0, 1, 2], [0, 0, -1]),
        ([0, 2, 3], [0, 0, -1]),
        # Top face
        ([4, 6, 5], [0, 0, 1]),
        ([4, 7, 6], [0, 0, 1]),
        # Front face
        ([0, 5, 1], [0, -1, 0]),
        ([0, 4, 5], [0, -1, 0]),
        # Back face
        ([3, 2, 6], [0, 1, 0]),
        ([3, 6, 7], [0, 1, 0]),
        # Left face
        ([0, 3, 7], [-1, 0, 0]),
        ([0, 7, 4], [-1, 0, 0]),
        # Right face
        ([1, 5, 6], [1, 0, 0]),
        ([1, 6, 2], [1, 0, 0])
    ]
    
    with open(filename, 'w') as f:
        f.write("solid Cube\n")
        
        for tri_indices, normal in triangles:
            # Write face normal
            f.write(f"  facet normal {normal[0]} {normal[1]} {normal[2]}\n")
            f.write("    outer loop\n")
            
            # Write the three vertices of the triangle
            for idx in tri_indices:
                v = vertices[idx]
                # Scale up by 10mm
                f.write(f"      vertex {v[0]*10} {v[1]*10} {v[2]*10}\n")
            
            f.write("    endloop\n")
            f.write("  endfacet\n")
        
        f.write("endsolid Cube\n")
    
    print(f"Created {filename} - a 10mm x 10mm x 10mm cube")

def create_tooth_stl(filename="sample_tooth.stl"):
    """Create a simplified tooth-like STL file."""
    import math
    
    # Create a simplified tooth crown shape
    with open(filename, 'w') as f:
        f.write("solid SimpleTooth\n")
        
        # Generate a simple cone-like tooth shape
        segments = 8
        height = 15  # 15mm tall
        base_radius = 5  # 5mm radius at base
        top_radius = 2   # 2mm radius at top
        
        # Generate vertices for base and top circles
        base_vertices = []
        top_vertices = []
        
        for i in range(segments):
            angle = (2 * math.pi * i) / segments
            # Base circle
            base_vertices.append([
                base_radius * math.cos(angle),
                base_radius * math.sin(angle),
                0
            ])
            # Top circle (crown)
            top_vertices.append([
                top_radius * math.cos(angle),
                top_radius * math.sin(angle),
                height
            ])
        
        # Create side faces
        for i in range(segments):
            next_i = (i + 1) % segments
            
            # Triangle 1: base to side
            f.write(f"  facet normal 0 0 0\n")
            f.write("    outer loop\n")
            f.write(f"      vertex {base_vertices[i][0]} {base_vertices[i][1]} {base_vertices[i][2]}\n")
            f.write(f"      vertex {base_vertices[next_i][0]} {base_vertices[next_i][1]} {base_vertices[next_i][2]}\n")
            f.write(f"      vertex {top_vertices[i][0]} {top_vertices[i][1]} {top_vertices[i][2]}\n")
            f.write("    endloop\n")
            f.write("  endfacet\n")
            
            # Triangle 2: side to top
            f.write(f"  facet normal 0 0 0\n")
            f.write("    outer loop\n")
            f.write(f"      vertex {base_vertices[next_i][0]} {base_vertices[next_i][1]} {base_vertices[next_i][2]}\n")
            f.write(f"      vertex {top_vertices[next_i][0]} {top_vertices[next_i][1]} {top_vertices[next_i][2]}\n")
            f.write(f"      vertex {top_vertices[i][0]} {top_vertices[i][1]} {top_vertices[i][2]}\n")
            f.write("    endloop\n")
            f.write("  endfacet\n")
        
        # Create base cap
        for i in range(1, segments - 1):
            f.write(f"  facet normal 0 0 -1\n")
            f.write("    outer loop\n")
            f.write(f"      vertex {base_vertices[0][0]} {base_vertices[0][1]} {base_vertices[0][2]}\n")
            f.write(f"      vertex {base_vertices[i][0]} {base_vertices[i][1]} {base_vertices[i][2]}\n")
            f.write(f"      vertex {base_vertices[i+1][0]} {base_vertices[i+1][1]} {base_vertices[i+1][2]}\n")
            f.write("    endloop\n")
            f.write("  endfacet\n")
        
        # Create top cap
        for i in range(1, segments - 1):
            f.write(f"  facet normal 0 0 1\n")
            f.write("    outer loop\n")
            f.write(f"      vertex {top_vertices[0][0]} {top_vertices[0][1]} {top_vertices[0][2]}\n")
            f.write(f"      vertex {top_vertices[i+1][0]} {top_vertices[i+1][1]} {top_vertices[i+1][2]}\n")
            f.write(f"      vertex {top_vertices[i][0]} {top_vertices[i][1]} {top_vertices[i][2]}\n")
            f.write("    endloop\n")
            f.write("  endfacet\n")
        
        f.write("endsolid SimpleTooth\n")
    
    print(f"Created {filename} - a simplified tooth model (15mm tall)")

if __name__ == "__main__":
    import os
    
    # Create samples in the media directory
    media_dir = "/var/www/fusion/media/sample_stl"
    os.makedirs(media_dir, exist_ok=True)
    
    cube_path = os.path.join(media_dir, "sample_cube.stl")
    tooth_path = os.path.join(media_dir, "sample_tooth.stl")
    
    create_cube_stl(cube_path)
    create_tooth_stl(tooth_path)
    
    print(f"\nSample STL files created in {media_dir}")
    print("You can test the viewer by uploading these files.")