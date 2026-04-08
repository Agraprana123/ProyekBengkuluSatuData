FROM ckan/ckan-base:2.11

USER root

RUN apt-get update && apt-get install -y netcat-openbsd

# Upgrade pip
RUN pip install --upgrade pip

# Install required Python packages
RUN pip install --no-cache-dir \
    geojson \
    shapely \
    fiona \
    pyproj \
    geoalchemy2 \
    pika \
    redis \
    factory_boy \
    pytest

# Install local extensions from src/
RUN pip install --no-cache-dir \
    git+https://github.com/ckan/ckanext-spatial.git

RUN pip install --no-cache-dir \
    git+https://github.com/ckan/ckanext-harvest.git
    
RUN pip install --no-cache-dir \
    git+https://github.com/ckan/ckanext-geoview.git

COPY src/ckanext-bengkulusatudata /srv/app/src/ckanext-bengkulusatudata
RUN pip install --no-cache-dir -e /srv/app/src/ckanext-bengkulusatudata

RUN pip install OWSLib==0.35.0
# Copy entrypoint scripts
COPY --chown=ckan-sys:ckan-sys ckan/docker-entrypoint.d/* /docker-entrypoint.d/

# Copy patches
COPY --chown=ckan-sys:ckan-sys ckan/patches ${APP_DIR}/patches

USER ckan

# Apply patches
RUN for d in $APP_DIR/patches/*; do \
        if [ -d "$d" ]; then \
            for f in `ls $d/*.patch 2>/dev/null | sort -g`; do \
                cd $SRC_DIR/`basename "$d"` && \
                echo "Applying patch $f" && \
                patch -p1 < "$f" ; \
            done ; \
        fi ; \
    done
